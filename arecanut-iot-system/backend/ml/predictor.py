import os
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    print("Warning: GEMINI_API_KEY not found in environment variables.")

class ArecanutLeafClassifier:
    def __init__(self, model_path=None):
        self.class_names = ["Fruit Rot", "Healthy", "Yellow Leaf"]
        # Use the recommended Gemini model for multimodal tasks
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def predict(self, image_path):
        if not api_key:
            return {
                "disease": "Error: Missing API Key",
                "confidence": 0.0,
                "risk_level": "Unknown"
            }

        try:
            # Open image using PIL
            img = Image.open(image_path)
            
            prompt = """
            You are an expert agricultural botanist specializing in Arecanut (Betel nut) diseases.
            Analyze this arecanut leaf image and classify its condition into exactly one of these categories:
            1. "Healthy"
            2. "Fruit Rot"
            3. "Yellow Leaf"
            
            Also, provide a confidence score between 0.0 and 1.0.
            
            Return the output STRICTLY as a JSON object with this exact format, and no other text or markdown formatting:
            {
                "disease": "Healthy",
                "confidence": 0.95
            }
            """
            
            response = self.model.generate_content([prompt, img])
            result_text = response.text.strip()
            
            # Clean up potential markdown formatting from Gemini response
            if result_text.startswith("```json"):
                result_text = result_text[7:-3].strip()
            elif result_text.startswith("```"):
                result_text = result_text[3:-3].strip()
                
            result = json.loads(result_text)
            
            disease = result.get("disease", "Unknown")
            
            # Validate disease category
            if disease not in self.class_names:
                disease = "Healthy" # Default fallback
                
            confidence = result.get("confidence", 0.0)
            
            return {
                "disease": disease,
                "confidence": round(float(confidence), 2),
                "risk_level": "High" if disease != "Healthy" else "Low"
            }
            
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return {
                "disease": "Error analyzing image",
                "confidence": 0.0,
                "risk_level": "Unknown"
            }

leaf_classifier = ArecanutLeafClassifier()
