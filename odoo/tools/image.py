# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import codecs
import io

from PIL import Image
from PIL import ImageEnhance
from random import randrange

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

# ----------------------------------------
# Image resizing
# ----------------------------------------

def image_resize_image(base64_source, size=(1024, 1024), encoding='base64', filetype=None, avoid_if_small=False, upper_limit=False):
    """ Function to resize an image. The image will be resized to the given
        size, while keeping the aspect ratios, and holes in the image will be
        filled with transparent background. The image will not be stretched if
        smaller than the expected size.
        Steps of the resizing:
        - Compute width and height if not specified.
        - if avoid_if_small: if both image sizes are smaller than the requested
          sizes, the original image is returned. This is used to avoid adding
          transparent content around images that we do not want to alter but
          just resize if too big. This is used for example when storing images
          in the 'image' field: we keep the original image, resized to a maximal
          size, without adding transparent content around it if smaller.
        - create a thumbnail of the source image through using the thumbnail
          function. Aspect ratios are preserved when using it. Note that if the
          source image is smaller than the expected size, it will not be
          extended, but filled to match the size.
        - create a transparent background that will hold the final image.
        - paste the thumbnail on the transparent background and center it.

        :param base64_source: base64-encoded version of the source
            image; if False, returns False
        :param size: 2-tuple(width, height). A None value for any of width or
            height mean an automatically computed value based respectively
            on height or width of the source image.
        :param encoding: the output encoding
        :param filetype: the output filetype, by default the source image's
        :type filetype: str, any PIL image format (supported for creation)
        :param avoid_if_small: do not resize if image height and width
            are smaller than the expected size.
    """
    if not base64_source:
        return False
    # Return unmodified content if no resize or we etect first 6 bits of '<'
    # (0x3C) for SVG documents - This will bypass XML files as well, but it's
    # harmless for these purposes
    if size == (None, None) or base64_source[:1] == b'P':
        return base64_source
    image_stream = io.BytesIO(codecs.decode(base64_source, encoding))
    image = Image.open(image_stream)
    # store filetype here, as Image.new below will lose image.format
    filetype = (filetype or image.format).upper()

    filetype = {
        'BMP': 'PNG',
    }.get(filetype, filetype)

    asked_width, asked_height = size
    if upper_limit:
        if asked_width:
            asked_width = min(asked_width, image.size[0])
        if asked_height:
            asked_height = min(asked_height, image.size[1])

        if image.size[0] >= image.size[1]:
            asked_height = None
        else:
            asked_width = None
        if asked_width is None and asked_height is None:
            return base64_source

    if asked_width is None:
        asked_width = int(image.size[0] * (float(asked_height) / image.size[1]))
    if asked_height is None:
        asked_height = int(image.size[1] * (float(asked_width) / image.size[0]))
    size = asked_width, asked_height
    # check image size: do not create a thumbnail if avoiding smaller images
    if avoid_if_small and image.size[0] <= size[0] and image.size[1] <= size[1]:
        return base64_source

    if image.size != size:
        image = image_resize_and_sharpen(image, size, upper_limit=upper_limit)
    if image.mode not in ["1", "L", "P", "RGB", "RGBA"] or (filetype == 'JPEG' and image.mode == 'RGBA'):
        image = image.convert("RGB")

    background_stream = io.BytesIO()
    image.save(background_stream, filetype)
    return codecs.encode(background_stream.getvalue(), encoding)

def image_resize_and_sharpen(image, size, preserve_aspect_ratio=False, factor=2.0, upper_limit=False):
    """
        Create a thumbnail by resizing while keeping ratio.
        A sharpen filter is applied for a better looking result.

        :param image: PIL.Image.Image()
        :param size: 2-tuple(width, height)
        :param preserve_aspect_ratio: boolean (default: False)
        :param factor: Sharpen factor (default: 2.0)
    """
    origin_mode = image.mode
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    image.thumbnail(size, Image.ANTIALIAS)
    if preserve_aspect_ratio:
        size = image.size
    sharpener = ImageEnhance.Sharpness(image)
    resized_image = sharpener.enhance(factor)
    # create a transparent image for background and paste the image on it
    if upper_limit:
        image = Image.new('RGBA', (size[0], size[1]-3), (255, 255, 255, 0)) # FIXME temporary fix for trimming the ghost border.
    else:
        image = Image.new('RGBA', size, (255, 255, 255, 0))
    image.paste(resized_image, ((size[0] - resized_image.size[0]) // 2, (size[1] - resized_image.size[1]) // 2))

    if image.mode != origin_mode:
        image = image.convert(origin_mode)
    return image

def image_save_for_web(image, fp=None, format=None):
    """
        Save image optimized for web usage.

        :param image: PIL.Image.Image()
        :param fp: File name or file object. If not specified, a bytestring is returned.
        :param format: File format if could not be deduced from image.
    """
    opt = dict(format=image.format or format)
    if image.format == 'PNG':
        opt.update(optimize=True)
        alpha = False
        if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
            alpha = image.convert('RGBA').split()[-1]
        if image.mode != 'P':
            # Floyd Steinberg dithering by default
            image = image.convert('RGBA').convert('P', palette=Image.WEB, colors=256)
        if alpha:
            image.putalpha(alpha)
    elif image.format == 'JPEG':
        opt.update(optimize=True, quality=80)
    if fp:
        image.save(fp, **opt)
    else:
        img = io.BytesIO()
        image.save(img, **opt)
        return img.getvalue()

def image_resize_image_big(base64_source, size=(1024, 1024), encoding='base64', filetype=None, avoid_if_small=True):
    """ Wrapper on image_resize_image, to resize images larger than the standard
        'big' image size: 1024x1024px.
        :param size, encoding, filetype, avoid_if_small: refer to image_resize_image
    """
    return image_resize_image(base64_source, size, encoding, filetype, avoid_if_small)

def image_resize_image_medium(base64_source, size=(128, 128), encoding='base64', filetype=None, avoid_if_small=False):
    """ Wrapper on image_resize_image, to resize to the standard 'medium'
        image size: 180x180.
        :param size, encoding, filetype, avoid_if_small: refer to image_resize_image
    """
    return image_resize_image(base64_source, size, encoding, filetype, avoid_if_small)

def image_resize_image_small(base64_source, size=(64, 64), encoding='base64', filetype=None, avoid_if_small=False):
    """ Wrapper on image_resize_image, to resize to the standard 'small' image
        size: 50x50.
        :param size, encoding, filetype, avoid_if_small: refer to image_resize_image
    """
    return image_resize_image(base64_source, size, encoding, filetype, avoid_if_small)

# ----------------------------------------
# Crop Image
# ----------------------------------------
def crop_image(data, type='top', ratio=None, size=None, image_format=None):
    """ Used for cropping image and create thumbnail
        :param data: base64 data of image.
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
    if not data:
        return False
    image_stream = Image.open(io.BytesIO(base64.b64decode(data)))
    output_stream = io.BytesIO()
    w, h = image_stream.size
    new_h = h
    new_w = w

    if ratio:
        w_ratio, h_ratio = ratio
        new_h = (w * h_ratio) // w_ratio
        new_w = w
        if new_h > h:
            new_h = h
            new_w = (h * w_ratio) // h_ratio

    image_format = image_format or image_stream.format or 'JPEG'
    if type == "top":
        cropped_image = image_stream.crop((0, 0, new_w, new_h))
        cropped_image.save(output_stream, format=image_format)
    elif type == "center":
        cropped_image = image_stream.crop(((w - new_w) // 2, (h - new_h) // 2, (w + new_w) // 2, (h + new_h) // 2))
        cropped_image.save(output_stream, format=image_format)
    elif type == "bottom":
        cropped_image = image_stream.crop((0, h - new_h, new_w, h))
        cropped_image.save(output_stream, format=image_format)
    else:
        raise ValueError('ERROR: invalid value for crop_type')
    if size:
        thumbnail = Image.open(io.BytesIO(output_stream.getvalue()))
        output_stream.truncate(0)
        output_stream.seek(0)
        thumbnail.thumbnail(size, Image.ANTIALIAS)
        thumbnail.save(output_stream, image_format)
    return base64.b64encode(output_stream.getvalue())

# ----------------------------------------
# Colors
# ---------------------------------------

def image_colorize(original, randomize=True, color=(255, 255, 255)):
    """ Add a color to the transparent background of an image.
        :param original: file object on the original image file
        :param randomize: randomize the background color
        :param color: background-color, if not randomize
    """
    # create a new image, based on the original one
    original = Image.open(io.BytesIO(original))
    image = Image.new('RGB', original.size)
    # generate the background color, past it as background
    if randomize:
        color = (randrange(32, 224, 24), randrange(32, 224, 24), randrange(32, 224, 24))
    image.paste(color, box=(0, 0) + original.size)
    image.paste(original, mask=original)
    # return the new image
    buffer = io.BytesIO()
    image.save(buffer, 'PNG')
    return buffer.getvalue()

# ----------------------------------------
# Misc image tools
# ---------------------------------------

def image_get_resized_images(base64_source, return_big=False, return_medium=True, return_small=True,
    big_name='image', medium_name='image_medium', small_name='image_small',
    avoid_resize_big=True, avoid_resize_medium=False, avoid_resize_small=False, sizes={}):
    """ Standard tool function that returns a dictionary containing the
        big, medium and small versions of the source image. This function
        is meant to be used for the methods of functional fields for
        models using images.

        Default parameters are given to be used for the getter of functional
        image fields,  for example with res.users or res.partner. It returns
        only image_medium and image_small values, to update those fields.

        :param base64_source: base64-encoded version of the source
            image; if False, all returned values will be False
        :param return_{..}: if set, computes and return the related resizing
            of the image
        :param {..}_name: key of the resized image in the return dictionary;
            'image', 'image_medium' and 'image_small' by default.
        :param avoid_resize_[..]: see avoid_if_small parameter
        :return return_dict: dictionary with resized images, depending on
            previous parameters.
    """
    return_dict = dict()
    size_big = sizes.get(big_name, (1024, 1024))
    size_medium = sizes.get(medium_name, (128, 128))
    size_small = sizes.get(small_name, (64, 64))
    if isinstance(base64_source, str):
        base64_source = base64_source.encode('ascii')
    if return_big:
        return_dict[big_name] = image_resize_image_big(base64_source, avoid_if_small=avoid_resize_big, size=size_big)
    if return_medium:
        return_dict[medium_name] = image_resize_image_medium(base64_source, avoid_if_small=avoid_resize_medium, size=size_medium)
    if return_small:
        return_dict[small_name] = image_resize_image_small(base64_source, avoid_if_small=avoid_resize_small, size=size_small)
    return return_dict

def image_resize_images(vals, big_name='image', medium_name='image_medium', small_name='image_small', sizes={}):
    """ Update ``vals`` with image fields resized as expected. """
    if vals.get(big_name):
        vals.update(image_get_resized_images(vals[big_name],
                        return_big=True, return_medium=True, return_small=True,
                        big_name=big_name, medium_name=medium_name, small_name=small_name,
                        avoid_resize_big=True, avoid_resize_medium=False, avoid_resize_small=False, sizes=sizes))
    elif vals.get(medium_name):
        vals.update(image_get_resized_images(vals[medium_name],
                        return_big=True, return_medium=True, return_small=True,
                        big_name=big_name, medium_name=medium_name, small_name=small_name,
                        avoid_resize_big=True, avoid_resize_medium=True, avoid_resize_small=False, sizes=sizes))
    elif vals.get(small_name):
        vals.update(image_get_resized_images(vals[small_name],
                        return_big=True, return_medium=True, return_small=True,
                        big_name=big_name, medium_name=medium_name, small_name=small_name,
                        avoid_resize_big=True, avoid_resize_medium=True, avoid_resize_small=True, sizes=sizes))
    elif big_name in vals or medium_name in vals or small_name in vals:
        vals[big_name] = vals[medium_name] = vals[small_name] = False

def limited_image_resize(content, width=None, height=None, crop=False, upper_limit=False, avoid_if_small=False):
    """
    :param content: bytes (should be an image)
    """
    if content:
        signatures = [b'\xFF\xD8\xFF', b'\x89PNG\r\n\x1A\n']
        decoded_content = base64.b64decode(content)
        is_image = any(decoded_content.startswith(signature) for signature in signatures)
        if (width or height) and is_image:
            height = int(height or 0)
            width = int(width or 0)
            if crop:
                return crop_image(content, type='center', size=(width, height), ratio=(1, 1))
            else:
                if not upper_limit:
                    # resize maximum 500*500
                    width = min(width, 500)
                    height = min(height, 500)
                return image_resize_image(
                    base64_source=content, size=(width or None, height or None), encoding='base64', upper_limit=upper_limit,
                    avoid_if_small=avoid_if_small)
    return content

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
