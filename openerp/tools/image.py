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
from PIL import Image
import StringIO

# ----------------------------------------
# Image resizing
# ----------------------------------------

def image_resize_image(base64_source, size=(1024, 1024), encoding='base64', filetype='PNG', avoid_if_small=False):
    """ Function to resize an image. The image will be resized to the given
        size, while keeping the aspect ratios, and holes in the image will be
        filled with transparent background. The image will not be stretched if
        smaller than the expected size.
        Steps of the resizing:
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
        - create a transparent background that will hold the final
          image.
        - past the thumbnail on the transparent background and center
          it.
        
        :param base64_source: base64-encoded version of the source
            image
        :param size: tuple(height, width)
        :param encoding: the output encoding
        :param filetype: the output filetype
        :param avoid_if_small: do not resize if image height and width
            are smaller than the expected size.
    """
    image_stream = io.BytesIO(base64_source.decode(encoding))
    image = Image.open(image_stream)
    # check image size: do not create a thumbnail if avoiding smaller images
    if avoid_if_small and image.size[0] <= size[0] and image.size[1] <= size[1]:
        return base64_source
    # create a thumbnail: will resize and keep ratios
    image.thumbnail(size, Image.ANTIALIAS)
    # create a transparent image for background
    background = Image.new('RGBA', size, (255, 255, 255, 0))
    # past the resized image on the background
    background.paste(image, ((size[0] - image.size[0]) / 2, (size[1] - image.size[1]) / 2))
    # return an encoded image
    background_stream = StringIO.StringIO()
    background.save(background_stream, filetype)
    return background_stream.getvalue().encode(encoding)

def image_resize_image_big(base64_source, size=(1204, 1204), encoding='base64', filetype='PNG'):
    """ Wrapper on image_resize_image, to resize images larger than the standard
        'big' image size: 1024x1024px.
        :param base64_source: base64 encoded source image. If False,
            the function returns False.
    """
    if not base64_source:
        return False
    return image_resize_image(base64_source, size, encoding, filetype, True)

def image_resize_image_medium(base64_source, size=(180, 180), encoding='base64', filetype='PNG'):
    """ Wrapper on image_resize_image, to resize to the standard 'medium'
        image size: 180x180.
        :param base64_source: base64 encoded source image. If False,
            the function returns False.
    """
    if not base64_source:
        return False
    return image_resize_image(base64_source, size, encoding, filetype)
    
def image_resize_image_small(base64_source, size=(50, 50), encoding='base64', filetype='PNG'):
    """ Wrapper on image_resize_image, to resize to the standard 'small' image
        size: 50x50.
        :param base64_source: base64 encoded source image. If False,
            the function returns False.
    """
    if not base64_source:
        return False
    return image_resize_image(base64_source, size, encoding, filetype)

# ----------------------------------------
# Misc image tools
# ---------------------------------------

def image_get_resized_images(base64_source, return_big=False, return_medium=True, return_small=True,
    big_name='image', medium_name='image_medium', small_name='image_small'):
    """ Standard tool function that returns a dictionary containing the
        big, medium and small versions of the source image. This function
        is meant to be used for the methods of functional fields for
        models using images.

        Default parameters are given to be used for the getter of functional
        image fields,  for example with res.users or res.partner. It returns
        only image_medium and image_small values, to update those fields.
        
        :param base64_source: if set to False, other values are set to False
            also. The purpose is to be linked to the fields that hold images in
            OpenERP and that are binary fields.
        :param return_big: if set, return_dict contains the 'big_name' entry
        :param return_medium: if set, return_dict contains the 'medium_name' entry
        :param return_small: if set, return_dict contains the 'small_name' entry
        :param big_name: name related to the big version of the image;
            'image' by default.
        :param medium_name: name related to the medium version of the
            image; 'image_medium' by default.
        :param small_name: name related to the small version of the
            image; 'image_small' by default.
        :return return_dict: dictionary with resized images, depending on
            previous parameters.
    """
    return_dict = dict()
    if return_big: return_dict[big_name] = image_resize_image_big(base64_source)
    if return_medium: return_dict[medium_name] = image_resize_image_medium(base64_source)
    if return_small: return_dict[small_name] = image_resize_image_small(base64_source)
    return return_dict