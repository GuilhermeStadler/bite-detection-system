import json
import random
from pathlib import Path

import numpy as np
import tensorflow as tf


APP_ROOT = Path(__file__).resolve().parent
MODEL_DIR = APP_ROOT / "models"
DATASET_ROOT = APP_ROOT / "datasets" / "bite_image_validity"
MODEL_PATH = MODEL_DIR / "bite_image_validity.keras"
REPORT_PATH = MODEL_DIR / "bite_image_validity_evaluation.json"

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 16
EPOCHS_HEAD = 20
EPOCHS_FINE_TUNE = 12
SEED = 42
VALIDATION_SPLIT = 0.2
TEST_SPLIT = 0.15
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
CLASS_FOLDERS = {"invalid": 0, "valid": 1}


def collect_samples():
    samples = []
    for folder_name, label in CLASS_FOLDERS.items():
        folder = DATASET_ROOT / folder_name
        if not folder.exists():
            raise FileNotFoundError(f"Pasta obrigatória não encontrada: {folder}")
        files = [
            path
            for path in folder.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ]
        if len(files) < 100:
            print(f"Aviso: {folder_name} tem {len(files)} imagens. Colete mais exemplos antes de usar em produção.")
        samples.extend((str(path), label) for path in sorted(files))

    if len({label for _, label in samples}) < 2:
        raise ValueError("O treino precisa de exemplos em valid/ e invalid/.")
    return samples


def split_samples(samples):
    random.seed(SEED)
    by_class = {label: [] for label in CLASS_FOLDERS.values()}
    for sample in samples:
        by_class[sample[1]].append(sample)

    train, validation, test = [], [], []
    for class_samples in by_class.values():
        random.shuffle(class_samples)
        test_count = max(1, int(round(len(class_samples) * TEST_SPLIT)))
        validation_count = max(1, int(round(len(class_samples) * VALIDATION_SPLIT)))
        test.extend(class_samples[:test_count])
        validation.extend(class_samples[test_count:test_count + validation_count])
        train.extend(class_samples[test_count + validation_count:])

    random.shuffle(train)
    random.shuffle(validation)
    random.shuffle(test)
    return train, validation, test


def decode_image(file_path, label):
    image_bytes = tf.io.read_file(file_path)
    image = tf.io.decode_image(image_bytes, channels=3, expand_animations=False)
    image.set_shape([None, None, 3])
    image = tf.image.resize(image, IMAGE_SIZE)
    image = tf.keras.applications.mobilenet_v2.preprocess_input(image)
    return image, tf.cast(label, tf.float32)


def make_dataset(samples, training):
    paths = [path for path, _ in samples]
    labels = [label for _, label in samples]
    dataset = tf.data.Dataset.from_tensor_slices((paths, labels))
    if training:
        dataset = dataset.shuffle(len(samples), seed=SEED, reshuffle_each_iteration=True)
    dataset = dataset.map(decode_image, num_parallel_calls=tf.data.AUTOTUNE)
    dataset = dataset.batch(BATCH_SIZE)
    return dataset.prefetch(tf.data.AUTOTUNE)


def build_model():
    augmentation = tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(0.10),
            tf.keras.layers.RandomZoom(0.15),
            tf.keras.layers.RandomContrast(0.20),
        ],
        name="validity_augmentation",
    )
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=IMAGE_SIZE + (3,),
        include_top=False,
        weights="imagenet",
    )
    base_model.trainable = False

    inputs = tf.keras.Input(shape=IMAGE_SIZE + (3,))
    x = augmentation(inputs)
    x = base_model(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.30)(x)
    x = tf.keras.layers.Dense(64, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.25)(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid")(x)

    model = tf.keras.Model(inputs, outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.0003),
        loss="binary_crossentropy",
        metrics=[
            "accuracy",
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
            tf.keras.metrics.AUC(name="auc"),
        ],
    )
    return model, base_model


def save_evaluation_report(model, test_dataset):
    y_true = []
    y_score = []
    for images, labels in test_dataset:
        scores = model.predict(images, verbose=0).reshape(-1)
        y_true.extend(labels.numpy().astype(int).tolist())
        y_score.extend(scores.tolist())

    y_pred = [1 if score >= 0.5 else 0 for score in y_score]
    tp = sum(1 for truth, pred in zip(y_true, y_pred) if truth == 1 and pred == 1)
    tn = sum(1 for truth, pred in zip(y_true, y_pred) if truth == 0 and pred == 0)
    fp = sum(1 for truth, pred in zip(y_true, y_pred) if truth == 0 and pred == 1)
    fn = sum(1 for truth, pred in zip(y_true, y_pred) if truth == 1 and pred == 0)

    report = {
        "threshold": 0.5,
        "test_images": len(y_true),
        "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "invalid_rejection_rate": round(tn / max(1, tn + fp), 4),
        "valid_retention_rate": round(tp / max(1, tp + fn), 4),
        "false_accept_rate": round(fp / max(1, fp + tn), 4),
        "false_reject_rate": round(fn / max(1, fn + tp), 4),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Relatório salvo em: {REPORT_PATH}")


def train():
    MODEL_DIR.mkdir(exist_ok=True)
    samples = collect_samples()
    train_samples, validation_samples, test_samples = split_samples(samples)

    train_dataset = make_dataset(train_samples, training=True)
    validation_dataset = make_dataset(validation_samples, training=False)
    test_dataset = make_dataset(test_samples, training=False)

    model, base_model = build_model()
    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_auc", mode="max", patience=6, restore_best_weights=True),
        tf.keras.callbacks.ModelCheckpoint(MODEL_PATH, monitor="val_auc", mode="max", save_best_only=True),
    ]

    model.fit(train_dataset, validation_data=validation_dataset, epochs=EPOCHS_HEAD, callbacks=callbacks)

    base_model.trainable = True
    for layer in base_model.layers[:-30]:
        layer.trainable = False

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.00003),
        loss="binary_crossentropy",
        metrics=[
            "accuracy",
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
            tf.keras.metrics.AUC(name="auc"),
        ],
    )
    model.fit(train_dataset, validation_data=validation_dataset, epochs=EPOCHS_FINE_TUNE, callbacks=callbacks)

    if MODEL_PATH.exists():
        model = tf.keras.models.load_model(MODEL_PATH)
    else:
        model.save(MODEL_PATH)
    save_evaluation_report(model, test_dataset)
    print(f"Modelo salvo em: {MODEL_PATH}")


if __name__ == "__main__":
    train()
