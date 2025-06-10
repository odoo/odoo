from PIL import Image, ImageFile

def patch_module():
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    # Preload PIL with the minimal subset of image formats we need
    Image.preinit()
    # Not part of the preinit set but should be safe enough for us
    from PIL import IcoImagePlugin  # noqa: PLC0415
    # Allow saving PDF streams in images
    from PIL import PdfImagePlugin  # noqa: PLC0415
    Image._initialized = 2
