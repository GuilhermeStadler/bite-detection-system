import json
import random
from pathlib import Path

import numpy as np
import tensorflow as tf


APP_ROOT = Path(__file__).resolve().parent
MODEL_DIR = APP_ROOT / "models"
MODEL_PATH = MODEL_DIR / "venom_bite_classifier.keras"
LABELS_PATH = MODEL_DIR / "venom_bite_labels.json"
DATASET_ROOT = APP_ROOT / "datasets" / "animais peconhentos bites"

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 8
EPOCHS_HEAD = 35
EPOCHS_FINE_TUNE = 25
SEED = 42
VALIDATION_SPLIT = 0.2
TEST_SPLIT = 0.1
MIN_VALIDATION_IMAGES_PER_CLASS = 1
MIN_TEST_IMAGES_PER_CLASS = 1
MIN_IMAGES_FOR_TEST_SPLIT = 12
TARGET_TRAIN_IMAGES_PER_CLASS = 80


CLASS_FOLDERS = {
    "aranha_marrom": "Picadas de aranha-marrom",
    "armadeira": "Picadas de aranha armadeira",
    "viuva_negra": "picadas de viuva negra",
    "escorpiao_amarelo": "Picada de escorpiao amarelo",
    "escorpiao_marrom": "picadas escorpião-marrom",
    "jararaca": "picada de jararaca",
    "cascavel": "Picadas Cascavel",
    "coral_verdadeira": "picadas coral verdadeira",
    "surucucu": "Picadas surucucu",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def collect_image_paths():
    samples = []
    class_names = list(CLASS_FOLDERS)

    for label_index, class_name in enumerate(class_names):
        folder = DATASET_ROOT / CLASS_FOLDERS[class_name]
        if not folder.exists():
            raise FileNotFoundError(f"Pasta não encontrada: {folder}")

        files = [
            file_path
            for file_path in folder.rglob("*")
            if file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTENSIONS
        ]
        if len(files) < 2:
            raise ValueError(f"A classe {class_name} precisa ter pelo menos 2 imagens.")
        if len(files) < 20:
            print(f"Aviso: {class_name} tem apenas {len(files)} imagens. Adicione mais imagens para melhorar a precisão.")

        samples.extend((str(file_path), label_index) for file_path in sorted(files))

    return samples, class_names


def split_samples(samples, class_count):
    random.seed(SEED)
    by_class = [[] for _ in range(class_count)]
    for file_path, label in samples:
        by_class[label].append((file_path, label))

    train_samples = []
    validation_samples = []
    test_samples = []

    for class_samples in by_class:
        random.shuffle(class_samples)
        sample_count = len(class_samples)
        test_count = 0
        if sample_count >= MIN_IMAGES_FOR_TEST_SPLIT:
            test_count = max(MIN_TEST_IMAGES_PER_CLASS, int(round(sample_count * TEST_SPLIT)))

        remaining_after_test = sample_count - test_count
        validation_count = max(MIN_VALIDATION_IMAGES_PER_CLASS, int(round(sample_count * VALIDATION_SPLIT)))
        validation_count = min(validation_count, max(1, remaining_after_test - 2))

        test_samples.extend(class_samples[:test_count])
        validation_samples.extend(class_samples[test_count:test_count + validation_count])
        train_samples.extend(class_samples[test_count + validation_count:])

    random.shuffle(train_samples)
    random.shuffle(validation_samples)
    random.shuffle(test_samples)
    return train_samples, validation_samples, test_samples


def balance_training_samples(train_samples, class_count):
    random.seed(SEED)
    by_class = [[] for _ in range(class_count)]
    for file_path, label in train_samples:
        by_class[label].append((file_path, label))

    balanced_samples = []
    for class_samples in by_class:
        if not class_samples:
            continue

        target_count = max(TARGET_TRAIN_IMAGES_PER_CLASS, len(class_samples))
        repeated = []
        while len(repeated) < target_count:
            shuffled = class_samples[:]
            random.shuffle(shuffled)
            repeated.extend(shuffled)
        balanced_samples.extend(repeated[:target_count])

    random.shuffle(balanced_samples)
    return balanced_samples


def build_class_weights(train_samples, class_count):
    counts = [0] * class_count
    for _, label in train_samples:
        counts[label] += 1

    total = sum(counts)
    return {
        class_index: total / (class_count * max(1, count))
        for class_index, count in enumerate(counts)
    }


def decode_image(file_path, label):
    image_bytes = tf.io.read_file(file_path)
    image = tf.io.decode_image(image_bytes, channels=3, expand_animations=False)
    image.set_shape([None, None, 3])
    image = tf.image.resize(image, IMAGE_SIZE)
    image = tf.keras.applications.mobilenet_v2.preprocess_input(image)
    return image, label


def make_dataset(samples, training):
    paths = [file_path for file_path, _ in samples]
    labels = [label for _, label in samples]

    dataset = tf.data.Dataset.from_tensor_slices((paths, labels))
    if training:
        dataset = dataset.shuffle(buffer_size=len(samples), seed=SEED)

    dataset = dataset.map(decode_image, num_parallel_calls=tf.data.AUTOTUNE)
    dataset = dataset.cache()
    if training:
        dataset = dataset.shuffle(buffer_size=len(samples), seed=SEED, reshuffle_each_iteration=True)
    dataset = dataset.batch(BATCH_SIZE)
    return dataset.prefetch(tf.data.AUTOTUNE)


def print_class_distribution(samples, class_names, title):
    counts = [0] * len(class_names)
    for _, label in samples:
        counts[label] += 1

    print(title)
    for class_name, count in zip(class_names, counts):
        print(f"  {class_name}: {count}")


def save_evaluation_report(model, test_dataset, class_names):
    y_true = []
    y_pred = []

    for _, labels in test_dataset:
        predictions = model.predict(_, verbose=0)
        y_true.extend(labels.numpy().tolist())
        y_pred.extend(np.argmax(predictions, axis=1).tolist())

    matrix = np.zeros((len(class_names), len(class_names)), dtype=int)
    for expected, predicted in zip(y_true, y_pred):
        matrix[expected][predicted] += 1

    per_class = []
    for index, class_name in enumerate(class_names):
        total = int(matrix[index].sum())
        correct = int(matrix[index][index])
        accuracy = correct / total if total else 0
        per_class.append(
            {
                "class_name": class_name,
                "test_images": total,
                "correct": correct,
                "accuracy": round(accuracy, 4),
            }
        )

    report = {
        "classes": class_names,
        "overall_accuracy": round(sum(int(matrix[i][i]) for i in range(len(class_names))) / max(1, len(y_true)), 4),
        "per_class": per_class,
        "confusion_matrix": matrix.tolist(),
    }

    report_path = MODEL_DIR / "venom_bite_evaluation.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Relatório de avaliação salvo em: {report_path}")


def build_model(class_count):
    data_augmentation = tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(0.12),
            tf.keras.layers.RandomZoom(0.18),
            tf.keras.layers.RandomTranslation(0.08, 0.08),
            tf.keras.layers.RandomContrast(0.25),
            tf.keras.layers.RandomBrightness(0.15),
        ],
        name="data_augmentation",
    )

    base_model = tf.keras.applications.MobileNetV2(
        input_shape=IMAGE_SIZE + (3,),
        include_top=False,
        weights="imagenet",
    )
    base_model.trainable = False

    inputs = tf.keras.Input(shape=IMAGE_SIZE + (3,))
    x = data_augmentation(inputs)
    x = base_model(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dropout(0.35)(x)
    x = tf.keras.layers.Dense(
        96,
        activation="relu",
        kernel_regularizer=tf.keras.regularizers.l2(0.0005),
    )(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dropout(0.30)(x)
    outputs = tf.keras.layers.Dense(
        class_count,
        activation="softmax",
        kernel_regularizer=tf.keras.regularizers.l2(0.0005),
    )(x)

    model = tf.keras.Model(inputs, outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.0005),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model, base_model


def train():
    MODEL_DIR.mkdir(exist_ok=True)
    samples, class_names = collect_image_paths()
    train_samples, validation_samples, test_samples = split_samples(samples, len(class_names))
    balanced_train_samples = balance_training_samples(train_samples, len(class_names))
    class_weights = build_class_weights(balanced_train_samples, len(class_names))

    train_dataset = make_dataset(balanced_train_samples, training=True)
    validation_dataset = make_dataset(validation_samples, training=False)
    test_dataset = make_dataset(test_samples, training=False) if test_samples else None

    model, base_model = build_model(len(class_names))
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=12,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.35,
            patience=4,
            min_lr=0.000001,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            MODEL_DIR / "venom_bite_classifier.best.keras",
            monitor="val_loss",
            save_best_only=True,
        ),
    ]

    print(f"Treino real: {len(train_samples)} imagens")
    print(f"Treino balanceado: {len(balanced_train_samples)} amostras por repetição + augmentation")
    print(f"Validação: {len(validation_samples)} imagens")
    print(f"Teste: {len(test_samples)} imagens")
    print(f"Classes: {', '.join(class_names)}")
    print_class_distribution(train_samples, class_names, "Distribuição de treino:")
    print_class_distribution(balanced_train_samples, class_names, "Distribuição balanceada usada no treino:")
    print_class_distribution(validation_samples, class_names, "Distribuição de validação:")
    if test_samples:
        print_class_distribution(test_samples, class_names, "Distribuição de teste:")

    model.fit(
        train_dataset,
        validation_data=validation_dataset,
        epochs=EPOCHS_HEAD,
        callbacks=callbacks,
        class_weight=class_weights,
    )

    base_model.trainable = True
    for layer in base_model.layers[:-35]:
        layer.trainable = False

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.00005),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    model.fit(
        train_dataset,
        validation_data=validation_dataset,
        epochs=EPOCHS_FINE_TUNE,
        callbacks=callbacks,
        class_weight=class_weights,
    )

    MODEL_DIR.mkdir(exist_ok=True)
    best_model_path = MODEL_DIR / "venom_bite_classifier.best.keras"
    if best_model_path.exists():
        model = tf.keras.models.load_model(best_model_path)

    model.save(MODEL_PATH)
    LABELS_PATH.write_text(json.dumps(class_names, indent=2), encoding="utf-8")
    if test_dataset is not None:
        save_evaluation_report(model, test_dataset, class_names)

    print(f"Modelo salvo em: {MODEL_PATH}")
    print(f"Rótulos salvos em: {LABELS_PATH}")


if __name__ == "__main__":
    train()
