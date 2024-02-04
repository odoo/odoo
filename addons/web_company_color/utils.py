# Copyright 2019 Alexandre Díaz <dev@redneboa.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
import math
from io import BytesIO

from PIL import Image


def n_rgb_to_hex(_r, _g, _b):
    return "#{:02x}{:02x}{:02x}".format(int(255 * _r), int(255 * _g), int(255 * _b))


def convert_to_image(field_binary):
    return Image.open(BytesIO(base64.b64decode(field_binary)))


def image_to_rgb(img):
    def normalize_vec3(vec3):
        _l = 1.0 / math.sqrt(vec3[0] * vec3[0] + vec3[1] * vec3[1] + vec3[2] * vec3[2])
        return (vec3[0] * _l, vec3[1] * _l, vec3[2] * _l)

    # Force Alpha Channel
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    width, height = img.size
    # Reduce pixels
    width, height = (max(1, int(width / 4)), max(1, int(height / 4)))
    img = img.resize((width, height))
    rgb_sum = [0, 0, 0]
    # Mix. image colors using addition method
    RGBA_WHITE = (255, 255, 255, 255)
    for i in range(0, height * width):
        rgba = img.getpixel((i % width, i / width))
        if rgba[3] > 128 and rgba != RGBA_WHITE:
            rgb_sum[0] += rgba[0]
            rgb_sum[1] += rgba[1]
            rgb_sum[2] += rgba[2]
    _r, _g, _b = normalize_vec3(rgb_sum)
    return (_r, _g, _b)
