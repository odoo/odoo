from base64 import b64encode, b64decode
from math import ceil
from io import BytesIO
from PIL import Image

def scale_image(image_bytes, scale=1.):
    if scale == 1.:
        return image_bytes
    out_bytes = BytesIO()
    im = Image.open(BytesIO(image_bytes))
    im.resize((ceil(im.size[0] * scale), ceil(im.size[1] * scale))).save(out_bytes, 'JPEG')
    return out_bytes.getvalue()

def scale_image_b64(image_b64, scale=1.):
    return b64encode(scale_image(b64decode(image_b64), scale=scale))
