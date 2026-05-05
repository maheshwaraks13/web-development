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
from .ml.predictor import leaf_classifier


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
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
db = client[DB_NAME]

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
    image: UploadFile = File(...)
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
            "prediction": prediction
        }

        # 4. Save to DB
        result = await db.telemetry.insert_one(record)
        
        # 5. Alert Logic
        alerts = []
        if prediction["disease"] != "Healthy":
            alerts.append(f"Disease Detected: {prediction['disease']}")
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

@app.post("/upload_manual")
async def upload_manual(
    image: UploadFile = File(...)
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
            "is_manual": True
        }

        result = await db.telemetry.insert_one(record)

        alerts = []
        if prediction["disease"] != "Healthy":
            alerts.append(f"Disease Detected: {prediction['disease']}")

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
async def get_telemetry(limit: int = 20):
    cursor = db.telemetry.find().sort("timestamp", -1).limit(limit)
    records = await cursor.to_list(length=limit)
    for r in records:
        r["_id"] = str(r["_id"])
    return records

@app.get("/api/latest")
async def get_latest():
    record = await db.telemetry.find_one(sort=[("timestamp", -1)])
    if record:
        record["_id"] = str(record["_id"])
        return record
    return {"message": "No data available"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
