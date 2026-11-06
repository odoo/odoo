from PIL import Image

im = Image.open(r"C:\Users\Rith2\AppData\Local\Temp\ai-chat-custom-attachment-temp-file-baa6a8f3-ed60-40ed-ae3a-2b9892a4df94-7877851138925868835.png")
print("Image dimensions:", im.size)

# Let's crop the top navigation and title area (y: 0 to 180)
# And save text-like ASCII representation of header / breadcrumbs
crop_top = im.crop((0, 0, min(im.width, 1788), 160)).convert("L")
w, h = crop_top.size
step_x = 8
step_y = 6
for y in range(0, h, step_y):
    row = ""
    for x in range(0, min(w, 1200), step_x):
        p = crop_top.getpixel((x, y))
        row += "#" if p < 80 else ("." if p < 180 else " ")
    if row.strip():
        print(row)
