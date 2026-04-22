import json
from pathlib import Path

import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input


TRAIN_DIR = "dataset_split/train"
VAL_DIR = "dataset_split/val"
TEST_DIR = "dataset_split/test"


MODEL_DIR = Path("model")
MODEL_PATH = MODEL_DIR / "plant_classifier.keras"
CLASS_NAMES_PATH = MODEL_DIR / "class_names.json"


IMG_SIZE = (224, 224)
BATCH_SIZE = 16
EPOCHS = 10
SEED = 42

MODEL_DIR.mkdir(exist_ok=True)


for path in [TRAIN_DIR, VAL_DIR, TEST_DIR]:
    if not Path(path).exists():
        raise FileNotFoundError(f"Папка не найдена: {path}")

print("Подпапки train:")
for p in Path(TRAIN_DIR).iterdir():
    if p.is_dir():
        print(" -", repr(p.name))


train_ds = tf.keras.utils.image_dataset_from_directory(
    TRAIN_DIR,
    image_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    seed=SEED
)

val_ds = tf.keras.utils.image_dataset_from_directory(
    VAL_DIR,
    image_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    seed=SEED,
    shuffle=False
)

test_ds = tf.keras.utils.image_dataset_from_directory(
    TEST_DIR,
    image_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    shuffle=False
)

train_class_names = train_ds.class_names
val_class_names = val_ds.class_names
test_class_names = test_ds.class_names

print("Классы train:", train_class_names)
print("Классы val:", val_class_names)
print("Классы test:", test_class_names)

if train_class_names != val_class_names or train_class_names != test_class_names:
    raise ValueError(
        "Классы в train, val и test не совпадают.\n"
        f"train: {train_class_names}\n"
        f"val: {val_class_names}\n"
        f"test: {test_class_names}"
    )

class_names = train_class_names
num_classes = len(class_names)

AUTOTUNE = tf.data.AUTOTUNE
train_ds = train_ds.prefetch(buffer_size=AUTOTUNE)
val_ds = val_ds.prefetch(buffer_size=AUTOTUNE)
test_ds = test_ds.prefetch(buffer_size=AUTOTUNE)


data_augmentation = models.Sequential([
    layers.RandomFlip("horizontal"),
    layers.RandomRotation(0.1),
    layers.RandomZoom(0.1),
    layers.RandomContrast(0.1),
])


base_model = MobileNetV2(
    input_shape=(224, 224, 3),
    include_top=False,
    weights="imagenet"
)

base_model.trainable = False


inputs = layers.Input(shape=(224, 224, 3))
x = data_augmentation(inputs)
x = preprocess_input(x)
x = base_model(x, training=False)
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dropout(0.3)(x)
outputs = layers.Dense(num_classes, activation="softmax")(x)

model = models.Model(inputs, outputs)

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)

model.summary()

callbacks = [
    tf.keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=3,
        restore_best_weights=True
    )
]

history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS,
    callbacks=callbacks
)


test_loss, test_acc = model.evaluate(test_ds)
print(f"\nТочность на test: {test_acc:.4f}")


model.save(MODEL_PATH)


with open(CLASS_NAMES_PATH, "w", encoding="utf-8") as f:
    json.dump(class_names, f, ensure_ascii=False, indent=2)

print(f"Модель сохранена в: {MODEL_PATH}")
print(f"Классы сохранены в: {CLASS_NAMES_PATH}")