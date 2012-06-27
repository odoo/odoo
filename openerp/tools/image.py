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

def resize_image(base64_source, size=(1024, 1024), encoding='base64', filetype='PNG', avoid_if_small=False):
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

def resize_image_big(base64_source, size=(1204, 1204), encoding='base64', filetype='PNG'):
    return resize_image(base64_source, size, encoding, filetype, True)

def resize_image_medium(base64_source, size=(180, 180), encoding='base64', filetype='PNG'):
    return resize_image(base64_source, size, encoding, filetype)
    
def resize_image_small(base64_source, size=(50, 50), encoding='base64', filetype='PNG'):
    return resize_image(base64_source, size, encoding, filetype)
