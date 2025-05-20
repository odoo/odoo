import base64
import io
import requests
from PIL import Image


def get_image_as_base64(url):
    response = requests.get(url)
    if response.status_code == 200:
        image = Image.open(io.BytesIO(response.content))

        # Convert image to RGB mode if it's RGBA
        if image.mode == 'RGBA':
            image = image.convert('RGB')

        buffer = io.BytesIO()
        image.save(buffer, format='JPEG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')  # Decode base64 to string
    return None
