import shutil
from PIL import Image

# Copy original high-res logo
shutil.copyfile("scratch/original_logo.png", "static/src/img/university_logo.png")

# Generate 128x128
im = Image.open("scratch/original_logo.png")
im128 = im.resize((128, 128), Image.Resampling.LANCZOS)
im128.save("static/src/img/university_logo_128.png")

print("Updated university_logo.png and university_logo_128.png with module logo")
