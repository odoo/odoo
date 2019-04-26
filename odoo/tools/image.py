# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import io

from PIL import Image
from random import randrange

from odoo.tools.translate import _


# Preload PIL with the minimal subset of image formats we need
Image.preinit()
Image._initialized = 2

# Maps only the 6 first bits of the base64 data, accurate enough
# for our purpose and faster than decoding the full blob first
FILETYPE_BASE64_MAGICWORD = {
    b'/': 'jpg',
    b'R': 'gif',
    b'i': 'png',
    b'P': 'svg+xml',
}

IMAGE_BIG_SIZE = (1024, 1024)
IMAGE_LARGE_SIZE = (256, 256)
IMAGE_MEDIUM_SIZE = (128, 128)
IMAGE_SMALL_SIZE = (64, 64)

# Arbitraty limit to fit most resolutions, including Nokia Lumia 1020 photo,
# 8K with a ratio up to 16:10, and almost all variants of 4320p
IMAGE_MAX_RESOLUTION = 45e6


# ----------------------------------------
# Image resizing
# ----------------------------------------

def image_resize_image(base64_source, size=IMAGE_BIG_SIZE, filetype=None):
    """ Function to resize an image. The image will be resized to the given
        size, while keeping the aspect ratios. The image will not be resized if
        smaller than the expected size.

        :param base64_source: base64-encoded version of the source
            image; if False, returns False
        :param size: 2-tuple(width, height). A None value for any of width or
            height mean an automatically computed value based respectively
            on height or width of the source image.
        :param filetype: the output filetype, by default the source image's
        :type filetype: str, any PIL image format (supported for creation)
    """
    if not base64_source:
        return False
    # Return unmodified content if no resize or we etect first 6 bits of '<'
    # (0x3C) for SVG documents - This will bypass XML files as well, but it's
    # harmless for these purposes
    if base64_source[:1] == b'P':
        return base64_source

    image = base64_to_image(base64_source)
    # store filetype here, as Image.new below will lose image.format
    filetype = (filetype or image.format).upper()

    filetype = {
        'BMP': 'PNG',
    }.get(filetype, filetype)

    if size and (size[0] or size[1]):
        w, h = image.size
        asked_width = size[0] or (w * size[1]) // h
        asked_height = size[1] or (h * size[0]) // w

        image.thumbnail((asked_width, asked_height), Image.LANCZOS)

    if image.mode not in ["1", "L", "P", "RGB", "RGBA"] or (filetype == 'JPEG' and image.mode == 'RGBA'):
        image = image.convert("RGB")

    return image_to_base64(image, filetype)


def image_optimize_for_web(base64_source, max_width=0, quality=80):
    """Return the given `base64_source` optimized for web usage.

    :param base64_source: the image base64 encoded
    :type base64_source: string or bytes

    :param max_width: max width for the image. No resize if 0 given or if
        the image is already smaller than the given value.
    :type max_width: int

    :param quality: quality setting to apply. Ignored if image is not JPEG.
        1 is worse, 100 is best. Default to 80.
        Set to 95 to keep the original quality.
    :type quality: int

    :return: optimized image base64 encoded
    :rtype: bytes

    :raise: ValueError if image too large
    """
    if base64_source[:1] == b'P':
        # don't process SVG
        return base64_source

    image = base64_to_image(base64_source)

    w, h = image.size
    if w * h > IMAGE_MAX_RESOLUTION:
        raise ValueError(_("Image size excessive, uploaded images must be smaller than %s million pixels.") % str(IMAGE_MAX_RESOLUTION / 10e6))

    # get the format of the original image (must be done before resize)
    opt = {'format': image.format}

    if max_width and w and max_width < w:
        image.thumbnail((max_width, (h * max_width) / w))

    if opt['format'] == 'PNG':
        opt['optimize'] = True
        alpha = False
        if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
            alpha = image.convert('RGBA').split()[-1]
        if image.mode != 'P':
            # Floyd Steinberg dithering by default
            image = image.convert('RGBA').convert('P', palette=Image.WEB, colors=256)
        if alpha:
            image.putalpha(alpha)
    elif opt['format'] == 'JPEG':
        opt['optimize'] = True
        opt['quality'] = quality
    elif opt['format'] == 'GIF':
        opt['optimize'] = True
    else:
        raise ValueError(_("Unsupported image format: %s. Only JPEG, PNG and GIF are supported.") % image.format)

    return image_to_base64(image, **opt)


def image_resize_image_big(base64_source, filetype=None):
    """ Wrapper on image_resize_image, to resize images larger than the standard
        'big' image size: 1024x1024px.
        Refer to image_resize_image for the parameters.
    """
    return image_resize_image(base64_source, IMAGE_BIG_SIZE, filetype)


def image_resize_image_large(base64_source, filetype=None):
    """ Wrapper on image_resize_image, to resize to the standard 'large'
        image size: 256x256.
        Refer to image_resize_image for the parameters.
    """
    return image_resize_image(base64_source, IMAGE_LARGE_SIZE, filetype)


def image_resize_image_medium(base64_source, filetype=None):
    """ Wrapper on image_resize_image, to resize to the standard 'medium'
        image size: 128x128.
        Refer to image_resize_image for the parameters.
    """
    return image_resize_image(base64_source, IMAGE_MEDIUM_SIZE, filetype)


def image_resize_image_small(base64_source, filetype=None):
    """ Wrapper on image_resize_image, to resize to the standard 'small' image
        size: 64x64.
        Refer to image_resize_image for the parameters.
    """
    return image_resize_image(base64_source, IMAGE_SMALL_SIZE, filetype)


# ----------------------------------------
# Crop Image
# ----------------------------------------

def crop_image(base64_source, type='top', ratio=None, size=None, image_format=None):
    """ Used for cropping image and create thumbnail
        :param base64_source: the image base64 encoded
        :param type: Used for cropping position possible
            Possible Values : 'top', 'center', 'bottom'
        :param ratio: Cropping ratio
            e.g for (4,3), (16,9), (16,10) etc
            send ratio(1,1) to generate square image
        :param size: Resize image to size
            e.g (200, 200)
            after crop resize to 200x200 thumbnail
        :param image_format: return image format PNG,JPEG etc
    """
    if not base64_source:
        return False
    image = base64_to_image(base64_source)
    w, h = image.size
    new_h = h
    new_w = w

    if ratio:
        w_ratio, h_ratio = ratio
        new_h = (w * h_ratio) // w_ratio
        new_w = w
        if new_h > h:
            new_h = h
            new_w = (h * w_ratio) // h_ratio

    image_format = image_format or image.format or 'JPEG'
    if type == "top":
        box = (0, 0, new_w, new_h)
    elif type == "center":
        box = ((w - new_w) // 2, (h - new_h) // 2, (w + new_w) // 2, (h + new_h) // 2)
    elif type == "bottom":
        box = (0, h - new_h, new_w, h)
    else:
        raise ValueError('ERROR: invalid value for crop_type')

    image = image.crop(box)

    if size:
        image.thumbnail(size, Image.LANCZOS)

    return image_to_base64(image, image_format)


# ----------------------------------------
# Colors
# ---------------------------------------

def image_colorize(base64_source, randomize=True, color=(255, 255, 255)):
    """ Add a color to the transparent background of an image.
        :param base64_source: the image base64 encoded
        :param randomize: randomize the background color
        :param color: background-color, if not randomize
    """
    # create a new image, based on the original one
    original = base64_to_image(base64_source)
    image = Image.new('RGB', original.size)
    # generate the background color, past it as background
    if randomize:
        color = (randrange(32, 224, 24), randrange(32, 224, 24), randrange(32, 224, 24))
    image.paste(color, box=(0, 0) + original.size)
    image.paste(original, mask=original)
    return image_to_base64(image, original.format)


# ----------------------------------------
# Misc image tools
# ---------------------------------------

def base64_to_image(base64_source):
    """Return a PIL image from the given `base64_source`.

    :param base64_source: the image base64 encoded
    :type base64_source: string or bytes

    :return: the PIL image
    :rtype: PIL.Image

    :raise: binascii.Error: if the base64 is incorrect
    :raise: OSError if the image can't be identified by PIL
    """
    return Image.open(io.BytesIO(base64.b64decode(base64_source)))


def image_to_base64(image, format, **params):
    """Return a base64_image from the given PIL `image` using `params`.

    :param image: the PIL image
    :type image: PIL.Image

    :param params: params to expand when calling PIL.Image.save()
    :type params: dict

    :return: the image base64 encoded
    :rtype: bytes
    """
    stream = io.BytesIO()
    image.save(stream, format=format, **params)
    return base64.b64encode(stream.getvalue())


def is_image_size_above(base64_source, size=IMAGE_BIG_SIZE):
    """Return whether or not the size of the given image `base64_source` is
    above the provided `size` (tuple: width, height).
    """
    if not base64_source:
        return False
    if base64_source[:1] == b'P':
        # False for SVG
        return False
    image = base64_to_image(base64_source)
    width, height = image.size
    return width > size[0] or height > size[1]


def image_get_resized_images(base64_source,
        big_name='image', large_name='image_large', medium_name='image_medium', small_name='image_small'):
    """ Standard tool function that returns a dictionary containing the
        big, medium, large and small versions of the source image.

        :param {..}_name: key of the resized image in the return dictionary;
            'image', 'image_large', 'image_medium' and 'image_small' by default.
            Set a key to False to not include it.

        Refer to image_resize_image for the other parameters.

        :return return_dict: dictionary with resized images, depending on
            previous parameters.
    """
    return_dict = dict()
    if big_name:
        return_dict[big_name] = image_resize_image_big(base64_source)
    if large_name:
        return_dict[large_name] = image_resize_image_large(base64_source)
    if medium_name:
        return_dict[medium_name] = image_resize_image_medium(base64_source)
    if small_name:
        return_dict[small_name] = image_resize_image_small(base64_source)
    return return_dict


def image_resize_images(vals,
        return_big=True, return_large=False, return_medium=True, return_small=True,
        big_name='image', large_name='image_large', medium_name='image_medium', small_name='image_small'):
    """ Update ``vals`` with image fields resized as expected. """
    big_image = vals.get(big_name)
    large_image = vals.get(large_name)
    medium_image = vals.get(medium_name)
    small_image = vals.get(small_name)

    biggest_image = big_image or large_image or medium_image or small_image

    if biggest_image:
        vals.update(image_get_resized_images(biggest_image,
            big_name=return_big and big_name, large_name=return_large and large_name, medium_name=return_medium and medium_name, small_name=return_small and small_name))
    elif any(f in vals for f in [big_name, large_name, medium_name, small_name]):
        if return_big:
            vals[big_name] = False
        if return_large:
            vals[large_name] = False
        if return_medium:
            vals[medium_name] = False
        if return_small:
            vals[small_name] = False


def limited_image_resize(base64_source, width=None, height=None, crop=False):
    """Return the given `base64_source` image resized to the given `width` and
    `height`. Return the original image if both `width` and `height` are fasly.

    :param base64_source: the image base64 encoded
    :type base64_source: string or bytes

    :param width: target width, or 0 to keep aspect ratio if height given
    :type width: int

    :param height: target height, or 0 to keep aspect ratio if width given
    :type height: int

    :param crop: True if the result should be cropped to a square.
        False to resize without cropping.
    :type crop: bool

    :return: resulting image base64 encoded
    :rtype: string or bytes
    """
    if base64_source and (width or height):
        if crop:
            return crop_image(base64_source, type='center', size=(width, height), ratio=(1, 1))
        else:
            return image_resize_image(base64_source=base64_source, size=(width, height))
    return base64_source


def image_data_uri(base64_source):
    """This returns data URL scheme according RFC 2397
    (https://tools.ietf.org/html/rfc2397) for all kind of supported images
    (PNG, GIF, JPG and SVG), defaulting on PNG type if not mimetype detected.
    """
    return 'data:image/%s;base64,%s' % (
        FILETYPE_BASE64_MAGICWORD.get(base64_source[:1], 'png'),
        base64_source.decode(),
    )


if __name__=="__main__":
    import sys

    assert len(sys.argv)==3, 'Usage to Test: image.py SRC.png DEST.png'

    img = base64.b64encode(open(sys.argv[1],'rb').read())
    new = image_resize_image(img, (128,100))
    open(sys.argv[2], 'wb').write(base64.b64decode(new))
