# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-today OpenERP s.a. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import io
import StringIO

from PIL import Image
from PIL import ImageOps
from random import random

# ----------------------------------------
# Image resizing
# ----------------------------------------

def image_resize_image(base64_source, size=(1024, 1024), encoding='base64', filetype='PNG', avoid_if_small=False):
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
            height mean an automatically computed value based respectivelly
            on height or width of the source image.
        :param encoding: the output encoding
        :param filetype: the output filetype
        :param avoid_if_small: do not resize if image height and width
            are smaller than the expected size.
    """
    if not base64_source:
        return False
    if size == (None, None):
        return base64_source
    image_stream = io.BytesIO(base64_source.decode(encoding))
    image = Image.open(image_stream)

    asked_width, asked_height = size
    if asked_width is None:
        asked_width = int(image.size[0] * (float(asked_height) / image.size[1]))
    if asked_height is None:
        asked_height = int(image.size[1] * (float(asked_width) / image.size[0]))
    size = asked_width, asked_height

    # check image size: do not create a thumbnail if avoiding smaller images
    if avoid_if_small and image.size[0] <= size[0] and image.size[1] <= size[1]:
        return base64_source

    if image.size <> size:
        # If you need faster thumbnails you may use use Image.NEAREST
        image = ImageOps.fit(image, size, Image.ANTIALIAS)
    if image.mode not in ["1", "L", "P", "RGB", "RGBA"]:
        image = image.convert("RGB")

    background_stream = StringIO.StringIO()
    image.save(background_stream, filetype)
    return background_stream.getvalue().encode(encoding)

def image_resize_image_big(base64_source, size=(1204, 1204), encoding='base64', filetype='PNG', avoid_if_small=True):
    """ Wrapper on image_resize_image, to resize images larger than the standard
        'big' image size: 1024x1024px.
        :param size, encoding, filetype, avoid_if_small: refer to image_resize_image
    """
    return image_resize_image(base64_source, size, encoding, filetype, avoid_if_small)

def image_resize_image_medium(base64_source, size=(128, 128), encoding='base64', filetype='PNG', avoid_if_small=False):
    """ Wrapper on image_resize_image, to resize to the standard 'medium'
        image size: 180x180.
        :param size, encoding, filetype, avoid_if_small: refer to image_resize_image
    """
    return image_resize_image(base64_source, size, encoding, filetype, avoid_if_small)

def image_resize_image_small(base64_source, size=(64, 64), encoding='base64', filetype='PNG', avoid_if_small=False):
    """ Wrapper on image_resize_image, to resize to the standard 'small' image
        size: 50x50.
        :param size, encoding, filetype, avoid_if_small: refer to image_resize_image
    """
    return image_resize_image(base64_source, size, encoding, filetype, avoid_if_small)

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
        color = (int(random() * 192 + 32), int(random() * 192 + 32), int(random() * 192 + 32))
    image.paste(color)
    image.paste(original, mask=original)
    # return the new image
    buffer = StringIO.StringIO()
    image.save(buffer, 'PNG')
    return buffer.getvalue()

# ----------------------------------------
# Misc image tools
# ---------------------------------------

def image_get_resized_images(base64_source, return_big=False, return_medium=True, return_small=True,
    big_name='image', medium_name='image_medium', small_name='image_small',
    avoid_resize_big=True, avoid_resize_medium=False, avoid_resize_small=False):
    """ Standard tool function that returns a dictionary containing the
        big, medium and small versions of the source image. This function
        is meant to be used for the methods of functional fields for
        models using images.

        Default parameters are given to be used for the getter of functional
        image fields,  for example with res.users or res.partner. It returns
        only image_medium and image_small values, to update those fields.

        :param base64_source: base64-encoded version of the source
            image; if False, all returnes values will be False
        :param return_{..}: if set, computes and return the related resizing
            of the image
        :param {..}_name: key of the resized image in the return dictionary;
            'image', 'image_medium' and 'image_small' by default.
        :param avoid_resize_[..]: see avoid_if_small parameter
        :return return_dict: dictionary with resized images, depending on
            previous parameters.
    """
    return_dict = dict()
    if return_big:
        return_dict[big_name] = image_resize_image_big(base64_source, avoid_if_small=avoid_resize_big)
    if return_medium:
        return_dict[medium_name] = image_resize_image_medium(base64_source, avoid_if_small=avoid_resize_medium)
    if return_small:
        return_dict[small_name] = image_resize_image_small(base64_source, avoid_if_small=avoid_resize_small)
    return return_dict


if __name__=="__main__":
    import sys

    assert len(sys.argv)==3, 'Usage to Test: image.py SRC.png DEST.png'

    img = file(sys.argv[1],'rb').read().encode('base64')
    new = image_resize_image(img, (128,100))
    file(sys.argv[2], 'wb').write(new.decode('base64'))

