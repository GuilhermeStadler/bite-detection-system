import os
import logging
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat


APP_ROOT = Path(__file__).resolve().parent
DEFAULT_VALIDITY_MODEL_PATH = APP_ROOT / "models" / "bite_image_validity.keras"
DEFAULT_VALIDITY_LABELS_PATH = APP_ROOT / "models" / "bite_image_validity_labels.json"
IMAGE_SIZE = (224, 224)
MIN_ANALYZABLE_DIMENSION = 64
MIN_LUMINANCE_STDDEV = 4.0
ANALYSIS_SIZE = 224
MIN_USABLE_BRIGHTNESS = 28.0
MAX_USABLE_BRIGHTNESS = 245.0
MIN_SHARPNESS = 0.45
MIN_SKIN_RATIO = 0.03
MIN_CLEAR_SKIN_RATIO = 0.10
MIN_VISUAL_CHANGE_SCORE = 0.018
MIN_WEAK_VISUAL_CHANGE_SCORE = 0.007
MAX_DARK_BACKGROUND_RATIO_FOR_UNCHANGED_SKIN = 0.08
MAX_SCENE_VARIATION_FOR_UNCHANGED_SKIN = 45.0

INVALID_IMAGE_MESSAGE = (
    "A imagem enviada não apresenta características suficientes para ser analisada pelo "
    "Bite Detection System. Verifique a imagem e as informações fornecidas ou envie uma nova imagem."
)
MISSING_VALIDITY_MODEL_MESSAGE = (
    "A imagem enviada não apresenta sinais visuais suficientes de picada ou alteração na pele. "
    "Envie uma foto mais próxima e nítida da região afetada, junto com os sintomas."
)

_validity_model = None
logger = logging.getLogger(__name__)


def _sample_image(image_path):
    with Image.open(image_path) as image:
        image = image.convert("RGB")
        original_size = image.size
        image.thumbnail((ANALYSIS_SIZE, ANALYSIS_SIZE))
        return image.copy(), original_size


def _is_skin_pixel(r, g, b):
    maximum = max(r, g, b)
    minimum = min(r, g, b)
    if r < 45 or g < 25 or b < 15:
        return False
    if maximum - minimum < 12:
        return False
    if r - g < 8:
        return False
    if r >= g >= b and r - b >= 12:
        return True
    if r > 95 and g > 55 and b > 40 and r > b and 8 <= abs(r - g) <= 65:
        return True
    return False


def _is_purple_or_bruised_pixel(r, g, b):
    return r >= 65 and b >= 50 and g <= max(r, b) * 0.86 and abs(r - b) <= 85


def _is_red_or_inflamed_pixel(r, g, b):
    return r >= 105 and r >= g * 1.16 and r >= b * 1.03 and g >= 35


def _is_dark_mark_pixel(r, g, b):
    luminance = (0.299 * r) + (0.587 * g) + (0.114 * b)
    return luminance < 72 and max(r, g, b) - min(r, g, b) > 10


def _sharpness_score(grayscale):
    edges = grayscale.filter(ImageFilter.FIND_EDGES)
    return float(ImageStat.Stat(edges).stddev[0])


def _visual_evidence_check(image_path):
    image, original_size = _sample_image(image_path)
    grayscale = image.convert("L")
    stat = ImageStat.Stat(grayscale)
    brightness = float(stat.mean[0])
    luminance_stddev = float(stat.stddev[0])
    sharpness = _sharpness_score(grayscale)

    pixel_source = image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()
    pixels = list(pixel_source)
    total = max(1, len(pixels))
    skin_count = 0
    skin_r = 0
    skin_g = 0
    skin_b = 0

    for r, g, b in pixels:
        is_skin = _is_skin_pixel(r, g, b)
        if is_skin:
            skin_count += 1
            skin_r += r
            skin_g += g
            skin_b += b

    skin_mean = None
    if skin_count:
        skin_mean = (skin_r / skin_count, skin_g / skin_count, skin_b / skin_count)

    purple_count = 0
    red_count = 0
    dark_mark_count = 0
    for r, g, b in pixels:
        if skin_mean:
            color_distance = ((r - skin_mean[0]) ** 2 + (g - skin_mean[1]) ** 2 + (b - skin_mean[2]) ** 2) ** 0.5
            if color_distance >= 34 and _is_purple_or_bruised_pixel(r, g, b):
                purple_count += 1
            if color_distance >= 30 and _is_red_or_inflamed_pixel(r, g, b):
                red_count += 1
        if _is_dark_mark_pixel(r, g, b):
            dark_mark_count += 1

    skin_ratio = skin_count / total
    purple_ratio = purple_count / total
    red_ratio = red_count / total
    dark_mark_ratio = dark_mark_count / total
    color_change_score = purple_ratio + red_ratio
    dark_mark_support = min(0.015, dark_mark_ratio * 0.35) if color_change_score >= MIN_WEAK_VISUAL_CHANGE_SCORE else 0
    visual_change_score = color_change_score + dark_mark_support

    debug = {
        "resolution": {"width": original_size[0], "height": original_size[1]},
        "brightness": round(brightness, 3),
        "luminance_stddev": round(luminance_stddev, 3),
        "sharpness": round(sharpness, 3),
        "skin_ratio": round(skin_ratio, 5),
        "purple_ratio": round(purple_ratio, 5),
        "red_ratio": round(red_ratio, 5),
        "dark_mark_ratio": round(dark_mark_ratio, 5),
        "color_change_score": round(color_change_score, 5),
        "dark_mark_support": round(dark_mark_support, 5),
        "visual_change_score": round(visual_change_score, 5),
        "skin_mean_rgb": tuple(round(value, 3) for value in skin_mean) if skin_mean else None,
        "thresholds": {
            "min_usable_brightness": MIN_USABLE_BRIGHTNESS,
            "max_usable_brightness": MAX_USABLE_BRIGHTNESS,
            "min_sharpness": MIN_SHARPNESS,
            "min_skin_ratio": MIN_SKIN_RATIO,
            "min_clear_skin_ratio": MIN_CLEAR_SKIN_RATIO,
            "min_visual_change_score": MIN_VISUAL_CHANGE_SCORE,
            "min_weak_visual_change_score": MIN_WEAK_VISUAL_CHANGE_SCORE,
            "max_dark_background_ratio_for_unchanged_skin": MAX_DARK_BACKGROUND_RATIO_FOR_UNCHANGED_SKIN,
            "max_scene_variation_for_unchanged_skin": MAX_SCENE_VARIATION_FOR_UNCHANGED_SKIN,
        },
    }

    if brightness < MIN_USABLE_BRIGHTNESS:
        return {
            "status": "rejected",
            "reason": "imagem escura demais para triagem visual",
            "message": INVALID_IMAGE_MESSAGE,
            "debug": {**debug, "blocking_rule": "brightness_below_minimum"},
        }

    if brightness > MAX_USABLE_BRIGHTNESS and luminance_stddev < 12:
        return {
            "status": "rejected",
            "reason": "imagem clara demais e sem detalhes analisáveis",
            "message": INVALID_IMAGE_MESSAGE,
            "debug": {**debug, "blocking_rule": "overexposed_without_detail"},
        }

    if sharpness < MIN_SHARPNESS and visual_change_score < MIN_VISUAL_CHANGE_SCORE:
        return {
            "status": "rejected",
            "reason": "imagem desfocada sem alteração visual reconhecível",
            "message": INVALID_IMAGE_MESSAGE,
            "debug": {**debug, "blocking_rule": "blur_without_visual_change"},
        }

    if skin_ratio < MIN_SKIN_RATIO and visual_change_score < MIN_VISUAL_CHANGE_SCORE:
        return {
            "status": "rejected",
            "reason": "imagem sem região de pele ou alteração visual compatível",
            "message": INVALID_IMAGE_MESSAGE,
            "debug": {**debug, "blocking_rule": "no_skin_or_visual_change"},
        }

    if (
        color_change_score < MIN_WEAK_VISUAL_CHANGE_SCORE
        and (
            dark_mark_ratio > MAX_DARK_BACKGROUND_RATIO_FOR_UNCHANGED_SKIN
            or luminance_stddev > MAX_SCENE_VARIATION_FOR_UNCHANGED_SKIN
        )
    ):
        return {
            "status": "rejected",
            "reason": "imagem parece mostrar ambiente ou objetos, sem alteração visível na pele",
            "message": MISSING_VALIDITY_MODEL_MESSAGE,
            "debug": {**debug, "blocking_rule": "scene_without_skin_change"},
        }

    if visual_change_score >= MIN_VISUAL_CHANGE_SCORE and skin_ratio >= MIN_SKIN_RATIO:
        return {
            "status": "passed",
            "reason": "pele com alteração visual compatível para triagem",
            "debug": {**debug, "blocking_rule": "none"},
        }

    if skin_ratio >= MIN_CLEAR_SKIN_RATIO or visual_change_score >= MIN_WEAK_VISUAL_CHANGE_SCORE:
        return {
            "status": "inconclusive",
            "reason": "região corporal detectada, mas alteração visual pouco evidente",
            "message": "",
            "debug": {**debug, "blocking_rule": "none"},
        }

    return {
        "status": "rejected",
        "reason": "imagem sem sinais visuais suficientes para triagem",
        "message": MISSING_VALIDITY_MODEL_MESSAGE,
        "debug": {**debug, "blocking_rule": "insufficient_skin_or_change"},
    }


def _technical_image_check(image_path):
    image, original_size = _sample_image(image_path)
    width, height = original_size
    if width < MIN_ANALYZABLE_DIMENSION or height < MIN_ANALYZABLE_DIMENSION:
        return {
            "status": "rejected",
            "reason": "imagem com resolução insuficiente para triagem visual",
            "message": INVALID_IMAGE_MESSAGE,
            "debug": {
                "resolution": {"width": width, "height": height},
                "thresholds": {"min_analyzable_dimension": MIN_ANALYZABLE_DIMENSION},
                "blocking_rule": "resolution_below_minimum",
            },
        }

    grayscale = image.convert("L")
    stat = ImageStat.Stat(grayscale)
    luminance_stddev = float(stat.stddev[0])
    return {
        "status": "passed",
        "reason": "checagens técnicas básicas aprovadas",
        "debug": {
            "resolution": {"width": width, "height": height},
            "luminance_stddev": round(luminance_stddev, 3),
            "thresholds": {"min_analyzable_dimension": MIN_ANALYZABLE_DIMENSION, "min_luminance_stddev": MIN_LUMINANCE_STDDEV},
            "blocking_rule": "none",
        },
    }


def _load_validity_model(model_path):
    global _validity_model

    if _validity_model is None:
        import tensorflow as tf

        _validity_model = tf.keras.models.load_model(model_path)

    return _validity_model


def _run_trained_validity_model(image_path, model_path):
    import tensorflow as tf

    model = _load_validity_model(model_path)
    image = tf.keras.preprocessing.image.load_img(image_path, target_size=IMAGE_SIZE)
    image = tf.keras.preprocessing.image.img_to_array(image)
    batch = tf.keras.applications.mobilenet_v2.preprocess_input(tf.expand_dims(image, axis=0))
    score = float(model.predict(batch, verbose=0)[0][0])

    return {
        "status": "passed" if score >= 0.5 else "rejected",
        "reason": "classificador binário de validade visual",
        "valid_image_score": score,
        "threshold": 0.5,
        "message": INVALID_IMAGE_MESSAGE if score < 0.5 else "",
    }


def evaluate_uploaded_image(image_path, model_path=None):
    technical_result = _technical_image_check(image_path)
    result = {
        "checked": True,
        "model_available": False,
        "status": technical_result["status"],
        "reason": technical_result["reason"],
        "message": technical_result.get("message", ""),
        "debug": technical_result.get("debug", {}),
    }
    logger.info("bite_image_gate technical_check=%s", result)
    if technical_result["status"] == "rejected":
        return result

    model_path = Path(model_path or DEFAULT_VALIDITY_MODEL_PATH)
    if not model_path.exists():
        if os.environ.get("BUGBITE_ALLOW_UNTRAINED_IMAGE_GATE", "").lower() in {"1", "true", "yes"}:
            result.update(
                {
                    "status": "not_trained",
                    "reason": "classificador de imagem válida x inválida ainda não treinado",
                }
            )
            logger.info("bite_image_gate final=%s", result)
            return result

        heuristic_result = _visual_evidence_check(image_path)
        result.update(heuristic_result)
        result["model_available"] = False
        result["valid_image_score"] = None
        result["reason"] = "{}; modelo treinado indisponível".format(heuristic_result["reason"])
        logger.info("bite_image_gate final=%s", result)
        return result

    trained_result = _run_trained_validity_model(image_path, model_path)
    result.update(trained_result)
    result["model_available"] = True
    logger.info("bite_image_gate final=%s", result)
    return result
