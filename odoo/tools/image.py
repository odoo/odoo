# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import io

from PIL import Image
# We can preload Ico too because it is considered safe
from PIL import IcoImagePlugin

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


class ImageProcess():

    def __init__(self, base64_source, verify_resolution=True):
        """Initialize the `base64_source` image for processing.

        :param base64_source: the original image base64 encoded
            No processing will be done if the `base64_source` is falsy or if
            the image is SVG.
        :type base64_source: string or bytes

        :param verify_resolution: if True, make sure the original image size is not
            excessive before starting to process it. The max allowed resolution is
            defined by `IMAGE_MAX_RESOLUTION`.
        :type verify_resolution: bool

        :return: self
        :rtype: ImageProcess

        :raise: ValueError if `verify_resolution` is True and the image is too large
        :raise: binascii.Error: if the base64 is incorrect
        :raise: OSError if the image can't be identified by PIL
        """
        self.base64_source = base64_source or False
        self.operationsCount = 0

        if not base64_source or base64_source[:1] in (b'P', 'P'):
            # don't process empty source or SVG
            self.image = False
        else:
            self.image = base64_to_image(self.base64_source)

            w, h = self.image.size
            if verify_resolution and w * h > IMAGE_MAX_RESOLUTION:
                raise ValueError(_("Image size excessive, uploaded images must be smaller than %s million pixels.") % str(IMAGE_MAX_RESOLUTION / 10e6))

            self.original_format = self.image.format.upper()

    def image_base64(self, quality=0, output_format=''):
        """Return the base64 encoded image resulting of all the image processing
        operations that have been applied previously.

        Return False if the initialized `base64_source` was falsy, and return
        the initialized `base64_source` without change if it was SVG.

        Also return the initialized `base64_source` if no operations have been
        applied and the `output_format` is the same as the original format and
        the quality is not specified.

        :param quality: quality setting to apply. Default to 0.
            - for JPEG: 1 is worse, 95 is best. Values above 95 should be
                avoided. Fasly values will fallback to 95, but only if the image
                was changed, otherwise the original image is returned.
            - for PNG: set falsy to prevent conversion to a WEB palette.
            - for other formats: no effect.
        :type quality: int

        :param output_format: the output format. Can be PNG, JPEG, GIF, or ICO.
            Default to the format of the original image. BMP is converted to
            PNG, other formats than those mentioned above are converted to JPEG.
        :type output_format: string

        :return: image base64 encoded or False
        :rtype: bytes or False
        """
        output_image = self.image

        if not output_image:
            return self.base64_source

        output_format = output_format.upper() or self.original_format
        if output_format == 'BMP':
            output_format = 'PNG'
        elif output_format not in ['PNG', 'JPEG', 'GIF', 'ICO']:
            output_format = 'JPEG'

        if not self.operationsCount and output_format == self.original_format and not quality:
            return self.base64_source

        opt = {'format': output_format}

        if output_format == 'PNG':
            opt['optimize'] = True
            if quality:
                if output_image.mode != 'P':
                    # Floyd Steinberg dithering by default
                    output_image = output_image.convert('RGBA').convert('P', palette=Image.WEB, colors=256)
        if output_format == 'JPEG':
            opt['optimize'] = True
            opt['quality'] = quality or 95
        if output_format == 'GIF':
            opt['optimize'] = True
            opt['save_all'] = True

        if output_image.mode not in ["1", "L", "P", "RGB", "RGBA"] or (output_format == 'JPEG' and output_image.mode == 'RGBA'):
            output_image = output_image.convert("RGB")

        return image_to_base64(output_image, **opt)

    def resize(self, max_width=0, max_height=0):
        """Resize the image.

        The image is never resized above the current image size. This method is
        only to create a smaller version of the image.

        The current ratio is preserved. To change the ratio, see `crop_resize`.

        If `max_width` or `max_height` is falsy, it will be computed from the
        other to keep the current ratio. If both are falsy, no resize is done.

        It is currently not supported for GIF because we do not handle all the
        frames properly.

        :param max_width: max width
        :type max_width: int

        :param max_height: max height
        :type max_height: int

        :return: self to allow chaining
        :rtype: ImageProcess
        """
        if self.image and self.image.format != 'GIF' and (max_width or max_height):
            w, h = self.image.size
            asked_width = max_width or (w * max_height) // h
            asked_height = max_height or (h * max_width) // w
            if asked_width != w or asked_height != h:
                self.image.thumbnail((asked_width, asked_height), Image.LANCZOS)
                if self.image.width != w or self.image.height != h:
                    self.operationsCount += 1
        return self

    def crop_resize(self, max_width, max_height, center_x=0.5, center_y=0.5):
        """Crop and resize the image.

        The image is never resized above the current image size. This method is
        only to create smaller versions of the image.

        Instead of preserving the ratio of the original image like `resize`,
        this method will force the output to take the ratio of the given
        `max_width` and `max_height`, so both have to be defined.

        The crop is done before the resize in order to preserve as much of the
        original image as possible. The goal of this method is primarily to
        resize to a given ratio, and it is not to crop unwanted parts of the
        original image. If the latter is what you want to do, you should create
        another method, or directly use the `crop` method from PIL.

        It is currently not supported for GIF because we do not handle all the
        frames properly.

        :param max_width: max width
        :type max_width: int

        :param max_height: max height
        :type max_height: int

        :param center_x: the center of the crop between 0 (left) and 1 (right)
            Default to 0.5 (center).
        :type center_x: float

        :param center_y: the center of the crop between 0 (top) and 1 (bottom)
            Default to 0.5 (center).
        :type center_y: float

        :return: self to allow chaining
        :rtype: ImageProcess
        """
        if self.image and self.image.format != 'GIF' and max_width and max_height:
            w, h = self.image.size
            # We want to keep as much of the image as possible -> at least one
            # of the 2 crop dimensions always has to be the same value as the
            # original image.
            # The target size will be reached with the final resize.
            if w / max_width > h / max_height:
                new_w, new_h = w, (max_height * w) // max_width
            else:
                new_w, new_h = (max_width * h) // max_height, h

            # No cropping above image size.
            if new_w > w:
                new_w, new_h = w, (new_h * w) // new_w
            if new_h > h:
                new_w, new_h = (new_w * h) // new_h, h

            # Corretly place the center of the crop.
            x_offset = (w - new_w) * center_x
            h_offset = (h - new_h) * center_y

            if new_w != w or new_h != h:
                self.image = self.image.crop((x_offset, h_offset, x_offset + new_w, h_offset + new_h))
                if self.image.width != w or self.image.height != h:
                    self.operationsCount += 1

        return self.resize(max_width, max_height)

    def colorize(self):
        """Replace the trasparent background by a random color.

        :return: self to allow chaining
        :rtype: ImageProcess
        """
        if self.image:
            original = self.image
            color = (randrange(32, 224, 24), randrange(32, 224, 24), randrange(32, 224, 24))
            self.image = Image.new('RGB', original.size)
            self.image.paste(color, box=(0, 0) + original.size)
            self.image.paste(original, mask=original)
            self.operationsCount += 1
        return self


def image_process(base64_source, size=(0, 0), verify_resolution=False, quality=0, crop=None, colorize=False, output_format=''):
    """Process the `base64_source` image by executing the given operations and
    return the result as a base64 encoded image.
    """
    if (not size or (not size[0] and not size[1])) and not verify_resolution and not quality and not crop and not colorize and not output_format:
        # for performance: don't do anything if no operations have been requested
        return base64_source

    image = ImageProcess(base64_source, verify_resolution)
    if size:
        if crop:
            center_x = 0.5
            center_y = 0.5
            if crop == 'top':
                center_y = 0
            elif crop == 'bottom':
                center_y = 1
            image.crop_resize(max_width=size[0], max_height=size[1], center_x=center_x, center_y=center_y)
        else:
            image.resize(max_width=size[0], max_height=size[1])
    if colorize:
        image.colorize()
    return image.image_base64(quality=quality, output_format=output_format)


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
    if base64_source[:1] in (b'P', 'P'):
        # False for SVG
        return False
    image = base64_to_image(base64_source)
    width, height = image.size
    return width > size[0] or height > size[1]


def image_guess_size_from_field_name(field_name):
    """Attempt to guess the image size based on `field_name`.

    If it can't be guessed, return (0, 0) instead.

    :param field_name: the name of a field
    :type field_name: string

    :return: the guessed size
    :rtype: tuple (width, height)
    """
    suffix = 'big' if field_name == 'image' else field_name.split('_')[-1]
    if suffix == 'big':
        return IMAGE_BIG_SIZE
    if suffix == 'large':
        return IMAGE_LARGE_SIZE
    if suffix == 'medium':
        return IMAGE_MEDIUM_SIZE
    if suffix == 'small':
        return IMAGE_SMALL_SIZE
    return (0, 0)


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
        return_dict[big_name] = image_process(base64_source, size=IMAGE_BIG_SIZE)
    if large_name:
        return_dict[large_name] = image_process(base64_source, size=IMAGE_LARGE_SIZE)
    if medium_name:
        return_dict[medium_name] = image_process(base64_source, size=IMAGE_MEDIUM_SIZE)
    if small_name:
        return_dict[small_name] = image_process(base64_source, size=IMAGE_SMALL_SIZE)
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
    new = image_process(img, size=(128, 100))
    open(sys.argv[2], 'wb').write(base64.b64decode(new))
