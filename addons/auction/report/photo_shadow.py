# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

def convert_catalog(from_file, to_file, size=220) :
    return __convert(from_file, to_file, size)

def convert(from_file, to_file):
    size = 95
    __convert(from_file, to_file, size=95)

def __convert(from_file, to_file, size=95):
    import Image, ImageDraw, ImageFilter
    im = Image.open(from_file)
    if float(im.size[1]/im.size[0])>2:
        im = im.resize((im.size[0]*size/im.size[1], size))
    else:
        im = im.resize((size,im.size[1]*size/im.size[0]))
    newimg = Image.new('RGB', (im.size[0]+8,im.size[1]+8), (255,255,255) )

    draw = ImageDraw.Draw(newimg)
    draw.rectangle((6, im.size[1]-5, im.size[0], im.size[1]+5), fill=(90,90,90))
    draw.rectangle((im.size[0]-5, 6, im.size[0]+5, im.size[1]), fill=(90,90,90))
    del draw 

    newimg = newimg.filter(ImageFilter.BLUR)
    newimg = newimg.filter(ImageFilter.BLUR)
    newimg = newimg.filter(ImageFilter.BLUR)

    newimg.paste(im, (0,0))
    draw = ImageDraw.Draw(newimg)
    draw.rectangle((0, 0, im.size[0], im.size[1]), outline=(0,0,0))
    del draw 
    to_fp = file(to_file, 'wb')
    newimg.save(to_fp, "JPEG")
    to_fp.close()
    res = newimg.size
    del im
    del newimg
    return res
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

