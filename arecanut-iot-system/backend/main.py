import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import motor.motor_asyncio
from datetime import datetime
import aiofiles
import uuid
import json

# ML Imports
from ml.predictor import leaf_classifier


app = FastAPI(title="Arecanut IoT Monitoring API")

# CORS for Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
UPLOAD_DIR = "uploads"
MONGODB_URL = "mongodb://localhost:27017"
DB_NAME = "arecanut_iot"

# Database Init
MONGODB_URL = "mongodb://localhost:27017"
DB_NAME = "arecanut_iot"
DATA_FILE = "db_fallback.json"

class LocalDBFallback:
    def __init__(self, filename):
        self.filename = filename
        if not os.path.exists(filename):
            with open(filename, 'w') as f:
                json.dump({"users": [], "telemetry": []}, f)
    
    def _read(self):
        try:
            with open(self.filename, 'r') as f:
                return json.load(f)
        except: return {"users": [], "telemetry": []}
            
    def _write(self, data):
        with open(self.filename, 'w') as f:
            json.dump(data, f, indent=4, default=str)

    class CollectionProxy:
        def __init__(self, parent, name):
            self.parent = parent
            self.name = name
            
        async def find_one(self, query, sort=None):
            data = self.parent._read().get(self.name, [])
            for item in data:
                match = True
                for k, v in query.items():
                    if item.get(k) != v:
                        match = False
                        break
                if match:
                    return item
            return None
            
        async def insert_one(self, doc):
            data = self.parent._read()
            if self.name not in data: data[self.name] = []
            if "_id" not in doc: doc["_id"] = str(uuid.uuid4())
            data[self.name].append(doc)
            self.parent._write(data)
            class Result:
                def __init__(self, id): self.inserted_id = id
            return Result(doc["_id"])
            
        def find(self, query=None):
            data = self.parent._read().get(self.name, [])
            results = []
            for item in data:
                if not query:
                    results.append(item)
                    continue
                match = True
                for k, v in query.items():
                    if item.get(k) != v:
                        match = False
                        break
                if match:
                    results.append(item)
            
            class CursorProxy:
                def __init__(self, items): self.items = items
                def sort(self, key, direction=-1):
                    self.items.sort(key=lambda x: x.get(key) or "", reverse=(direction == -1))
                    return self
                def limit(self, n):
                    self.items = self.items[:n]
                    return self
                async def to_list(self, length):
                    return self.items[:length]
            return CursorProxy(results)

    def __getitem__(self, name):
        return self.CollectionProxy(self, name)

# Global DB object
db = None

async def init_db():
    global db
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=1000)
        await client.admin.command('ping')
        db = client[DB_NAME]
        print("Connected to MongoDB successfully")
    except Exception:
        print("MongoDB connection failed. Using local JSON fallback (db_fallback.json)")
        db = LocalDBFallback(DATA_FILE)

@app.on_event("startup")
async def startup_event():
    await init_db()

# Static files for uploaded images
app.mount("/images", StaticFiles(directory=UPLOAD_DIR), name="images")

@app.get("/")
async def root():
    return {"message": "Arecanut Disease Monitoring API is running"}



@app.post("/upload")
async def upload_telemetry(
    temperature: float = Form(...),
    humidity: float = Form(...),
    moisture: float = Form(...),
    image: UploadFile = File(...),
    user_id: Optional[str] = Form(None)
):
    try:
        # 1. Save Image
        file_extension = image.filename.split(".")[-1]
        file_id = str(uuid.uuid4())
        filename = f"{file_id}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await image.read()
            await out_file.write(content)

        # 2. Disease Prediction
        prediction = leaf_classifier.predict(file_path)

        # 3. Create Record
        record = {
            "timestamp": datetime.utcnow(),
            "temperature": temperature,
            "humidity": humidity,
            "moisture": moisture,
            "image_url": f"/images/{filename}",
            "prediction": prediction,
            "user_id": user_id
        }

        # 4. Save to DB
        result = await db.telemetry.insert_one(record)
        
        # 5. Alert Logic
        alerts = []
        if prediction.get("status") == "success":
            disease_name = prediction.get("prediction", "Healthy")
            if disease_name != "Healthy":
                alerts.append(f"Disease Detected: {disease_name}")
        else:
            alerts.append(f"Image Analysis Error: {prediction.get('message', 'Unknown error')}")
            
        if humidity > 85:
            alerts.append("High Humidity Warning! Increased disease risk.")

        return {
            "status": "success",
            "id": str(result.inserted_id),
            "prediction": prediction,
            "alerts": alerts
        }
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from auth import UserCreate, UserLogin, create_access_token, get_current_user, get_password_hash, verify_password
from fastapi import Depends

@app.post("/register")
async def register(user: UserCreate):
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    user_dict = user.model_dump() if hasattr(user, 'model_dump') else user.dict()
    user_dict["password"] = hashed_password
    await db.users.insert_one(user_dict)
    return {"message": "User registered successfully"}

@app.post("/login")
async def login(user: UserLogin):
    db_user = await db.users.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": str(db_user["_id"])})
    return {"access_token": access_token, "token_type": "bearer", "name": db_user["name"]}

@app.post("/upload_manual")
async def upload_manual(
    image: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    try:
        file_extension = image.filename.split(".")[-1]
        file_id = str(uuid.uuid4())
        filename = f"{file_id}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await image.read()
            await out_file.write(content)

        prediction = leaf_classifier.predict(file_path)

        record = {
            "timestamp": datetime.utcnow(),
            "image_url": f"/images/{filename}",
            "prediction": prediction,
            "is_manual": True,
            "user_id": current_user
        }

        result = await db.telemetry.insert_one(record)

        alerts = []
        if prediction.get("status") == "success":
            disease_name = prediction.get("prediction", "Healthy")
            if disease_name != "Healthy":
                alerts.append(f"Disease Detected: {disease_name}")
        else:
            alerts.append(f"Image Analysis Error: {prediction.get('message', 'Unknown error')}")

        return {
            "status": "success",
            "id": str(result.inserted_id),
            "prediction": prediction,
            "alerts": alerts
        }
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/telemetry")
async def get_telemetry(limit: int = 20, current_user: str = Depends(get_current_user)):
    # Filter by user_id to ensure data isolation
    cursor = db.telemetry.find({"user_id": current_user}).sort("timestamp", -1).limit(limit)
    records = await cursor.to_list(length=limit)
    for r in records:
        r["_id"] = str(r["_id"])
    return records

@app.get("/api/latest")
async def get_latest(current_user: str = Depends(get_current_user)):
    # Get latest data specifically for the logged-in user
    record = await db.telemetry.find_one({"user_id": current_user}, sort=[("timestamp", -1)])
    if record:
        record["_id"] = str(record["_id"])
        return record
    return {"message": "No data available"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
