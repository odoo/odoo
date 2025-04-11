import PIL


def patch_module():
    try:
        from PIL.Image import Palette, Resampling, Transpose  # noqa: F401, PLC0415
    except ImportError:
        PIL.Image.Transpose = PIL.Image
        PIL.Image.Palette = PIL.Image
        PIL.Image.Resampling = PIL.Image

    # Preload PIL with the minimal subset of image formats we need
    PIL.Image.preinit()
    PIL.Image._initialized = 2
