#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include "DHT.h"

// --- Configuration ---
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* serverUrl = "http://YOUR_SERVER_IP:8000/upload"; // Backend endpoint

// --- Pin Definitions ---
#define DHTPIN 14          // DHT22 Pin
#define DHTTYPE DHT22      
#define SOIL_PIN 13        // Analog Soil Moisture Pin

// --- Camera Pins (AI-Thinker ESP32-CAM) ---
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  dht.begin();
  
  // Camera configuration
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if(psramFound()){
    config.frame_size = FRAMESIZE_UXGA;
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }

  // Init Camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  // Connect Wi-Fi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    sendData();
  }
  delay(300000); // Wait 5 minutes (300,000 ms)
}

void sendData() {
  // 1. Read Sensors
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  int soil = analogRead(SOIL_PIN);
  float moisturePercent = map(soil, 4095, 0, 0, 100);

  if (isnan(h) || isnan(t)) {
    Serial.println("Failed to read from DHT sensor!");
    return;
  }

  // 2. Capture Image
  camera_fb_t * fb = esp_camera_fb_get();
  if(!fb) {
    Serial.println("Camera capture failed");
    return;
  }

  // 3. Prepare Multipart Request
  Serial.println("Sending data to server...");
  HTTPClient http;
  http.begin(serverUrl);
  
  String boundary = "--------------------------" + String(millis(), HEX);
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);

  // Build Body
  String body = "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"temperature\"\r\n\r\n" + String(t) + "\r\n";
  
  body += "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"humidity\"\r\n\r\n" + String(h) + "\r\n";
  
  body += "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"moisture\"\r\n\r\n" + String(moisturePercent) + "\r\n";
  
  body += "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"image\"; filename=\"capture.jpg\"\r\n";
  body += "Content-Type: image/jpeg\r\n\r\n";

  // Note: For large images, we need to send in chunks or use a more memory-efficient way.
  // Here we'll try to send it in one go if ESP32 has enough buffer.
  
  int totalLength = body.length() + fb->len + boundary.length() + 6; // --boundary--\r\n is 6 chars
  
  int httpResponseCode = http.sendRequest("POST", (uint8_t*)body.c_str(), body.length(), fb->buf, fb->len, 
                                          (uint8_t*)("\r\n--" + boundary + "--\r\n").c_str(), boundary.length() + 6);

  if (httpResponseCode > 0) {
    Serial.printf("Response code: %d\n", httpResponseCode);
  } else {
    Serial.printf("Error code: %s\n", http.errorToString(httpResponseCode).c_str());
  }

  http.end();
  esp_camera_fb_return(fb); // Release buffer
}
