# -*- coding: utf-8 -*-
#
# Copyright (C) 2000-2005 by Yasushi Saito (yasushi.saito@gmail.com)
# 
# Jockey is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.
#
# Jockey is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
import sys
import pychart_util
import string
import re
import math
import theme
import os
import basecanvas
from scaling import *

try:
    import zlib
    _zlib_available_p = 1
except:
    _zlib_available_p = 0

class pdf_stream(object):
    def __init__(self, fp):
        self.fp = fp
        self.off = 0
    def write(self, str):
        self.fp.write(str)
        self.off += len(str)
    def tell(self):
        return self.off
        
def to_radian(deg):
    return deg*2*math.pi / 360.0

class T(basecanvas.T):
    def __init__(self, fname, compress_p_):
        basecanvas.T.__init__(self)
        self.__out_fname = fname
        self.__reset_context()
        self.__next_obj_id = 1
        self.__next_font_id = 1
        self.__obj_offsets = {}
        self.__registered_fonts = {}
        self.__lines = []
        self.__nr_gsave = 0

	if compress_p_ and not _zlib_available_p:
	    pychart_util.warn("Zlib not available. Compression request ignored.\n")
	    compress_p_ = 0
        self.__compress_p = compress_p_

    def __intern_font(self, name):
        "Assign an ID to the font NAME. Return its ID." 
        if not self.__registered_fonts.has_key(name):
            self.__registered_fonts[name] = self.__next_font_id
            self.__next_font_id += 1
        return self.__registered_fonts[name]

    def __define_obj(self, fp, str):
        obj_id = self.__next_obj_id
        self.__next_obj_id += 1
        self.__obj_offsets[obj_id] = fp.tell()
        fp.write("%d 0 obj\n%s\nendobj\n" % (obj_id, str))
        return obj_id

    def __define_stream_obj(self, fp, s):
        if self.__compress_p:
            p = zlib.compress(s)
            return self.__define_obj(fp, "<</Length %d/Filter/FlateDecode>>\nstream\n%sendstream"
                              % (len(p), p))
        else:            
            return self.__define_obj(fp, "<</Length %d\n>>\nstream\n%s\nendstream"
                              % (len(s), s))

    def __define_font_obj(self, fp, name, font_id):
        obj_id = self.__define_obj(fp, """<</Type/Font /Subtype/Type1 /Name/F%d /BaseFont/%s /Encoding/MacRomanEncoding>>""" % (font_id, name))
        return obj_id

    def __reset_context(self):
        self.__font_name = None
        self.__font_size = -1
        self.__line_style = None
        self.__fill_color = None
        self.__stroke_color = None
        self.__mtx_pushed = 0

    def newpath(self):
        pass
    def set_fill_color(self, color):
        if self.__fill_color == color:
            return
        if color.r == color.g and color.r == color.b:
            self.__write("%f g\n" % (color.r))
            self.__write("%f G\n" % (color.r))
        else:
            self.__write("%f %f %f rg\n" % (color.r, color.g, color.b))
            self.__write("%f %f %f RG\n" % (color.r, color.g, color.b))
        self.__fill_color = color
    def set_stroke_color(self, color):
        self.set_fill_color(color)
        return
                
    def __arcsub(self, x, y, radius, start, theta):
	xcos = math.cos(to_radian(theta))
	xsin = math.sin(to_radian(theta))
	x0 = radius * xcos
	y0 = radius * xsin
 	x1 = radius * (4-xcos)/3.0
 	y1 = radius * (1-xcos)*(xcos-3)/(3*xsin)

        xx0, xy0 = pychart_util.rotate(x0, y0, start+theta)
        xx1, xy1 = pychart_util.rotate(x1, -y1, start+theta)
        xx2, xy2 = pychart_util.rotate(x1, y1, start+theta)
	self.__write("%f %f %f %f %f %f c\n" %
		(x+xx1, y+xy1, x+xx2, y+xy2, x+xx0, y+xy0))
    def path_arc(self, x, y, radius, ratio, start, end):
        self.comment("PATHARC %f %f %f %f %f %f\n"
        	     % (x, y, radius, ratio, start, end))
        step = 10
        if radius < 10:
            step = 20
        if radius < 5:
            step = 30
        if ratio != 1.0:
            self.push_transformation((x, y), (1, ratio), None)
            deg = start
            while deg < end:
                theta = min(step, end-deg)
                self.__arcsub(x, y, radius, deg, theta/2)
                deg += theta
            self.pop_transformation()
        else:
            deg = start
            while deg < end:
                theta = min(step, end-deg)
                self.__arcsub(x, y, radius, deg, theta/2)
                deg += theta
        self.comment("end PATHARC\n")

    def text_begin(self):
        self.__write("BT ")
        self.__font_name = None
        self.__font_size = None
        
    def text_end(self):
        self.__write("ET\n")
    def text_moveto(self, x, y, angle):
	if angle != None:
	    xcos = math.cos(to_radian(angle))
	    xsin = math.sin(to_radian(angle))
	    self.__write("%f %f %f %f %f %f Tm " % (xcos, xsin, -xsin, xcos, x, y))
	else:
	    self.__write("1 0 0 1 %f %f Tm " % (x, y))

    def text_show(self, font_name, font_size, color, str):
        if self.__font_name  != font_name or self.__font_size != font_size:
            font_id = self.__intern_font(font_name)
            self.__write("/F%d %d Tf " % (font_id, font_size))
            self.__font_name = font_name
            self.__font_size = font_size
        self.set_fill_color(color)
        self.__write("(%s) Tj " % (str))

    def push_transformation(self, baseloc, scale, angle, in_text = 0):
        if in_text:
            op = "Tm"
        else:
            op = "cm"
            self.gsave()
            
        if baseloc == None:
            baseloc = (0,0)

        if angle != None:
            radian = to_radian(angle)
            self.__write("%f %f %f %f %f %f %s\n" %
                         (math.cos(radian), math.sin(radian),
                          -math.sin(radian), math.cos(radian),
                          baseloc[0], baseloc[1], op))
        if scale != None:
            self.__write("%f 0 0 %f %f %f %s\n" % (scale[0], scale[1],
                                                   baseloc[0],
                                                   baseloc[1], op))
        
    def pop_transformation(self, in_text = 0):
        if not in_text:
            self.grestore()
    def closepath(self):
        self.__write("h\n")
    def clip_sub(self):
        self.__write("W n\n")
    def fill(self):
        self.__write("f n\n")
    def gsave(self):
        self.__write("q\n")
    def grestore(self):
        self.__write("Q\n")
        self.__reset_context()
        
    def moveto(self, x, y):
        self.__write('%f %f m ' % (x, y))
    def lineto(self, x, y):
        self.__write("%f %f l\n" % (x, y))
    def stroke(self):
        self.__write("S\n")

    def set_line_style(self, style):
        if (self.__line_style == style):
            pass
        else:
            self.set_stroke_color(style.color)
            self.__write("%f w " % nscale(style.width))
            if style.dash != None:
                self.__write("[%s] 0 d\n" %
                             " ".join(map(str, nscale_seq(style.dash))))
            else:
                self.__write("[] 0 d\n")
            self.__write("%d j %d J\n" % (style.cap_style, style.join_style))
            self.__line_style = style        
    
    def comment(self, str):
        if not self.__compress_p:
            self.__write("%%" + str + "\n")

    def verbatim(self, str):
        self.__write(str)

    def __write(self, str):
        self.__lines.append(str)
        
#    def setbb(self, xmin, ymin, xmax, ymax):
#        self.__xmin = xmin
#        self.__ymin = ymin
#        self.__xmax = xmax
#        self.__ymax = ymax
        
    def close(self):
        basecanvas.T.close(self)
	if self.__lines == []:
	    return

        _fp, need_close = self.open_output(self.__out_fname)
        fp = pdf_stream(_fp)

        fp.write("%PDF-1.2\n")

        stream_obj_id = self.__define_stream_obj(fp, " ".join(self.__lines))

        fontstr = ""
        for font_name, font_id in self.__registered_fonts.items():
            obj_id = self.__define_font_obj(fp, font_name, font_id)
            fontstr += "/F%d %d 0 R " % (font_id, obj_id)
        
        pages_obj_id = self.__define_obj(fp, " <</Type/Pages /Kids [%d 0 R] /Count 1 >>" % (self.__next_obj_id + 1))

        bbox = theme.adjust_bounding_box([xscale(self.__xmin), yscale(self.__ymin),
                                          xscale(self.__xmax), yscale(self.__ymax)])
        
        page_obj_id = self.__define_obj(fp, """  <</Type/Page
\t/Parent %d 0 R
\t/Contents %d 0 R
\t/MediaBox [%d %d %d %d]
\t/Resources << /ProcSet [/PDF /Text]
\t\t/Font << %s >>
>> >>""" % (pages_obj_id, stream_obj_id, 
            bbox[0], bbox[1], bbox[2], bbox[3], fontstr))

        info_str = "/Producer (%s)\n/CreationDate (%s)" % (self.creator, self.creation_date)
        
        if self.title:
            info_str += "\n/Title (%s)" % (self.title, )
        if self.author:
            info_str += "\n/Author (%s)" % (self.author, )
            
        info_obj_id = self.__define_obj(fp, """<<%s>>""" % info_str)
        catalog_obj_id = self.__define_obj(fp, """  <</Type/Catalog/Pages %d 0 R>>""" % (pages_obj_id))

        xref_offset = fp.tell()
        fp.write("xref\n0 %d\n" % (len(self.__obj_offsets)+1))
        fp.write("0000000000 65535 f \n")
        id = 1
        while id <= len(self.__obj_offsets):
            fp.write("%010d 00000 n \n" % (self.__obj_offsets[id]))
            id += 1
        fp.write("trailer << /Size %d /Root %d 0 R /Info %d 0 R\n>>\n" % (len(self.__obj_offsets)+1, catalog_obj_id, info_obj_id))
        fp.write("startxref\n%d\n%%%%EOF\n" % xref_offset)

        if need_close:
            _fp.close()
