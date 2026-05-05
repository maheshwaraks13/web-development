# Arecanut IoT Disease Monitoring System

## Overview
This system uses an ESP32-CAM to monitor arecanut leaves and environmental conditions (Temperature, Humidity, Soil Moisture). It uses a CNN (MobileNetV2) to detect diseases like Fruit Rot and Yellow Leaf.

## Project Structure
- `firmware/`: ESP32-CAM Arduino code.
- `backend/`: FastAPI server with ML integration.
- `ml_model/`: Training scripts and model definition.
- `dashboard/`: Premium web interface.

## Quick Start

### 1. Backend Setup
```bash
cd backend
pip install -r requirements.txt
# Ensure MongoDB is running locally
python main.py
```

### 2. Firmware Setup
- Open `firmware/firmware.ino` in Arduino IDE.
- Install `DHT sensor library` and `ESP32` board support.
- Update `ssid`, `password`, and `serverUrl` (with your PC's IP).
- Upload to ESP32-CAM using a USB-to-TTL programmer.

### 3. Dashboard
- Simply open `dashboard/index.html` in your browser.
- It will automatically connect to `localhost:8000`.

### 4. Training (Optional)
- Place leaf images in `ml_model/dataset/Fruit Rot`, `ml_model/dataset/Healthy`, etc.
- Run `python ml_model/train.py` to generate `arecanut_model.h5`.
