import random
import uuid
from datetime import datetime
from fastapi import FastAPI, UploadFile, File

app = FastAPI(title="Arecanut IoT Simulation API")

# Configuration for random ranges
TEMP_RANGE = (20.0, 35.0)          # Celsius
HUMIDITY_RANGE = (40.0, 90.0)     # Percent
MOISTURE_RANGE = (10.0, 80.0)      # Percent
DISEASES = ["Healthy", "Fruit Rot", "Yellow Leaf Disease"]
ADVICE_MAP = {
    "Healthy": "Continue standard care.",
    "Fruit Rot": "Suggest fungicide application and moisture control.",
    "Yellow Leaf Disease": "Suggest nutrient management and soil treatment."
}

def random_float(rng):
    return round(random.uniform(*rng), 2)

def random_prediction():
    disease = random.choice(DISEASES)
    confidence = round(random.uniform(0.7, 0.99), 2)
    advice = ADVICE_MAP[disease]
    return {
        "status": "success",
        "prediction": disease,
        "confidence": confidence,
        "advice": advice,
        "disease": disease,   # backward compatibility for existing UI
        "confidence": confidence
    }

@app.get("/simulate/latest")
async def get_latest():
    # Return the most recent simulated telemetry record
    record = {
        "_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "temperature": random_float(TEMP_RANGE),
        "humidity": random_float(HUMIDITY_RANGE),
        "moisture": random_float(MOISTURE_RANGE),
        "image_url": "/images/placeholder.jpg",
        "prediction": random_prediction()
    }
    return record

@app.get("/simulate/telemetry")
async def get_telemetry(limit: int = 20):
    # Generate a list of simulated telemetry records
    records = []
    for _ in range(limit):
        rec = {
            "_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "temperature": random_float(TEMP_RANGE),
            "humidity": random_float(HUMIDITY_RANGE),
            "moisture": random_float(MOISTURE_RANGE),
            "image_url": "/images/placeholder.jpg",
            "prediction": random_prediction(),
            "is_manual": random.choice([True, False])
        }
        records.append(rec)
    return records

@app.post("/simulate/upload_manual")
async def upload_manual(image: UploadFile = File(...)):
    # Accept an image file but ignore its content; return a simulated prediction response.
    prediction = random_prediction()
    record = {
        "_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "image_url": f"/images/{uuid.uuid4()}.jpg",
        "prediction": prediction,
        "is_manual": True
    }
    return {"status": "success", "record": record, "prediction": prediction}

# ---------------------------------------------------------------------------
# Run a quick demo when the script is executed directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("simulation:app", host="0.0.0.0", port=8000, reload=True)
