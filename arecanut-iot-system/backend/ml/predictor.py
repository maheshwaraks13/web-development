import os
import google.generativeai as genai
from PIL import Image, ImageFilter
from dotenv import load_dotenv
import json
import numpy as np

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
        self.class_names = ["Fruit Rot", "Healthy", "Yellow Leaf Disease"]
        # Use the recommended Gemini model for multimodal tasks
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def preprocess_image(self, image_path):
        """
        Perform image preprocessing:
        - Resize image to model input size (224x224)
        - Remove noise if necessary
        - Normalize pixel values (handled conceptually, Gemini uses standard images)
        """
        img = Image.open(image_path).convert('RGB')
        
        # 1. Resize to 224x224
        img = img.resize((224, 224))
        
        # 2. Remove noise (slight blur / smoothing)
        img = img.filter(ImageFilter.SMOOTH_MORE)
        
        # 3. Normalization (we could convert to numpy, normalize and back, 
        # but PIL + Gemini just needs a standard image object).
        # We demonstrate normalization for CNNs below:
        img_array = np.array(img) / 255.0
        
        return img

    def predict(self, image_path):
        if not api_key:
            return {
                "status": "error",
                "message": "API key missing. Cannot process image."
            }

        try:
            # Apply preprocessing
            processed_img = self.preprocess_image(image_path)
            
            prompt = """
            You are an expert agricultural botanist specializing in Arecanut (Betel nut) diseases.
            Analyze this uploaded image and perform the following tasks:
            
            1. Identify if the image contains:
               - Healthy arecanut leaf/nut
               - Fruit Rot Disease
               - Yellow Leaf Disease
            
            2. If the image is unclear or NOT a plant (or not an arecanut plant/leaf/nut), return an error.
            
            3. If a disease is detected, provide short actionable advice:
               - For Fruit Rot: suggest fungicide application and moisture control
               - For Yellow Leaf Disease: suggest nutrient management and soil treatment
               - For Healthy: suggest continuing standard care
            
            Return the output STRICTLY as a JSON object and nothing else. Do not use markdown blocks like ```json.
            
            If valid image:
            {
               "status": "success",
               "prediction": "<disease_name>",
               "confidence": "<percentage as float, e.g. 0.95>",
               "advice": "<recommended action for farmer>"
            }
            
            If the image is unclear or not a plant:
            {
               "status": "error",
               "message": "Invalid or unclear image. Please capture a clear arecanut leaf image using the laptop camera."
            }
            """
            
            response = self.model.generate_content([prompt, processed_img])
            result_text = response.text.strip()
            
            # Clean up potential markdown formatting from Gemini response
            if result_text.startswith("```json"):
                result_text = result_text[7:-3].strip()
            elif result_text.startswith("```"):
                result_text = result_text[3:-3].strip()
                
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                 return {
                    "status": "error",
                    "message": "Error parsing model response."
                }
            
            if result.get("status") == "error":
                return result
                
            prediction = result.get("prediction", "Healthy")
            # Map predictions to match expected names if there's slight variation
            if "Fruit Rot" in prediction:
                prediction = "Fruit Rot"
            elif "Yellow Leaf" in prediction:
                prediction = "Yellow Leaf Disease"
            else:
                prediction = "Healthy"
                
            confidence = result.get("confidence", 0.0)
            
            # Fallback advice if model didn't provide one properly
            advice = result.get("advice", "")
            if not advice:
                if prediction == "Fruit Rot":
                    advice = "Suggest fungicide application and moisture control."
                elif prediction == "Yellow Leaf Disease":
                    advice = "Suggest nutrient management and soil treatment."
                else:
                    advice = "Continue standard care."
                    
            # In order to keep compatibility with existing main.py code expecting "disease", 
            # we will return the requested format but also include "disease" key temporarily
            # so the main.py doesn't break, OR we update main.py. Let's return exact format
            # but main.py will need a quick update.
            return {
                "status": "success",
                "prediction": prediction,
                "confidence": round(float(confidence), 2),
                "advice": advice,
                "disease": prediction # Kept for backward compatibility with main.py alerts
            }
            
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return {
                "status": "error",
                "message": f"Error analyzing image: {str(e)}"
            }

leaf_classifier = ArecanutLeafClassifier()
