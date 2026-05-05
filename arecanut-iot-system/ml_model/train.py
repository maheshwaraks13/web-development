import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from predictor import ArecanutLeafClassifier
import os

# Configuration
DATASET_PATH = "dataset/" # User should provide this
MODEL_NAME = "arecanut_model.h5"
BATCH_SIZE = 32
EPOCHS = 10

def train_model():
    if not os.path.exists(DATASET_PATH):
        print(f"Error: Dataset path '{DATASET_PATH}' does not exist.")
        print("Please create folder 'dataset' with subfolders: 'Fruit Rot', 'Healthy', 'Yellow Leaf'")
        return

    # Data Augmentation
    train_datagen = ImageDataGenerator(
        rescale=1./255,
        rotation_range=20,
        width_shift_range=0.2,
        height_shift_range=0.2,
        horizontal_flip=True,
        validation_split=0.2
    )

    train_generator = train_datagen.flow_from_directory(
        DATASET_PATH,
        target_size=(224, 224),
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        subset='training'
    )

    val_generator = train_datagen.flow_from_directory(
        DATASET_PATH,
        target_size=(224, 224),
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        subset='validation'
    )

    # Initialize model
    classifier = ArecanutLeafClassifier()
    model = classifier.model

    # Phase 1: Train top layers
    print("Training top layers...")
    model.fit(train_generator, validation_data=val_generator, epochs=5)

    # Phase 2: Fine-tuning
    print("Fine-tuning base model...")
    model.layers[0].trainable = True
    # Fine-tune only from specific layer onwards
    for layer in model.layers[0].layers[:100]:
        layer.trainable = False
        
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-5), loss='categorical_crossentropy', metrics=['accuracy'])
    model.fit(train_generator, validation_data=val_generator, epochs=EPOCHS)

    # Save
    model.save(MODEL_NAME)
    print(f"Model saved to {MODEL_NAME}")

if __name__ == "__main__":
    train_model()
