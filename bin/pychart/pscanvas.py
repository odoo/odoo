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
import re
import theme
import version
import basecanvas
from scaling import *

comment_p = 0

class T(basecanvas.T):
    def __init__(self, fname):
        basecanvas.T.__init__(self)
        self.__out_fname = fname
        self.__reset_context()
        self.__output_lines = []
        self.__nr_gsave = 0
        self.__font_ids = {}
        self.__nr_fonts = 0
        
    def __reset_context(self):
        self.__font_name = None
        self.__font_size = -1
        self.__line_style = None
        self.__color = None
        self.__mtx_pushed = 0
        self.__txtmtx_pushed = 0

    def __intern_font(self, name):
        if self.__font_ids.has_key(name):
            return self.__font_ids[name]
        id = "F%d" % self.__nr_fonts
        self.__nr_fonts += 1
        self.__font_ids[name] = id
        return id
    
    def newpath(self):
        self.__write("N\n")
    def stroke(self):
        self.__write("ST\n")
    def closepath(self):
        self.__write("CP\n")
    def moveto(self, x, y):
        self.__write('%g %g M\n' % (x, y))
    
    def set_fill_color(self, color):
        if self.__color == color:
            pass
        else:
            if color.r == color.g and color.r == color.b:
                self.__write("%g SG\n" % color.r)
            else:
                self.__write("%g %g %g SC\n" % (color.r, color.g, color.b))
	    self.__color = color
    def set_stroke_color(self, color):
        self.set_fill_color(color)
        
    def set_line_style(self, style):
        self.set_stroke_color(style.color)
        if (self.__line_style == style):
            pass
        else:
            self.__write("%g %d %d " % (nscale(style.width), 
				      style.cap_style, style.join_style))
            if style.dash != None:
                self.__write("[%s] 0 SLD " % 
                           " ".join(map(str, nscale_seq(style.dash))))
            else:
                self.__write("SL ")
        self.__line_style = style
            
    def gsave(self):
        self.__nr_gsave += 1
        self.__write("GS\n")
    def grestore(self):
        self.__write("GR\n")
        self.__nr_gsave -= 1
        self.__reset_context()

    def clip_sub(self):
        self.__write("clip\n")
        
    def path_arc(self, x, y, radius, ratio, start_angle, end_angle):
        self.push_transformation((x, y), (1, ratio), None)
        self.__write("0 0 %g %g %g arc\n" % (radius, start_angle, end_angle))
        self.pop_transformation()

    def curveto(self, a,b,c,d,e,f):    
        self.__write("%g %g %g %g %g %g curveto\n" % (a,b,c,d,e,f))

    def push_transformation(self, baseloc, scale, angle, in_text=0):
        self.__mtx_pushed += 1
        self.__write("GB\n")
        if baseloc != None:
            self.__write("%g %g T\n" % (baseloc[0], baseloc[1]))
        if angle != None and angle != 0:
            self.__write("%g R\n" % (angle))
        if scale != None:
            self.__write("%g %g scale\n" % (scale[0], scale[1]))
    def pop_transformation(self, in_text=0):
        if self.__mtx_pushed == 0:
            raise ValueError, "mtx not pushed"
        self.__mtx_pushed -= 1
        self.__write("GE\n")
    def text_begin(self):
        self.__txtmtx_pushed += 1
        self.__write("TB\n")
    def text_end(self):
        self.__txtmtx_pushed -= 1
	self.__write("TE\n")
    def text_moveto(self, x, y, angle):
	self.__write("%g %g T " % (x,y))
	if angle != None and angle != 0:
	    self.__write("%g R " % angle)
	self.moveto(0, 0)
        
    def text_show(self, font_name, size, color, str):
        self.set_fill_color(color)
        if (self.__font_name == font_name and self.__font_size == size):
            pass
        else:
            id = self.__intern_font(font_name)
            self.__write("%g %s\n" % (size, id))
            self.__font_name = font_name
            self.__font_size = size
        self.__write("(%s) show\n" % (str))

    def _path_polygon(self, points):
        if (len(points) == 4 
            and points[0][0] == points[1][0] 
            and points[2][0] == points[3][0] 
            and points[0][1] == points[3][1] 
            and points[1][1] == points[2][1]):
            # a rectangle.
            (xmin, ymin, xmax, ymax) = basecanvas._compute_bounding_box(points)
            if basecanvas.invisible_p(xmax, ymax):
                return
            self.setbb(xmin, ymin)
            self.setbb(xmax, ymax)
            self.__write("%g %g %g %g RECT\n" % \
                       (xscale(points[0][0]), yscale(points[0][1]),
                        xscale(points[2][0]), yscale(points[2][1])))
        else:
            basecanvas.T._path_polygon(self, points)
            
    def lineto(self, x, y):
        self.__write("%g %g L\n" % (x, y))
    def fill(self):
        self.__write("fill\n")
    def comment(self, str):
        if comment_p:
            self.verbatim("%" + str)
    def verbatim(self, str):
        self.__write(str)
        
    def close(self):
        basecanvas.T.close(self)
	if self.__output_lines == []:
	    return

        fp, need_close = self.open_output(self.__out_fname)
            
        if self.__nr_gsave != 0:
            raise Exception, "gsave misnest (%d)" % (self.__nr_gsave)
        self.write_preamble(fp)
        
        fp.writelines(self.__output_lines)
        fp.writelines(["showpage end\n",
                       "%%Trailer\n",
                       "%%EOF\n"])
        if need_close:
            fp.close()
            
    def __write(self, str):
        self.__output_lines.append(str)
    
    def writelines(self, l):
        self.__output_lines.extend(l)

    def write_preamble(self, fp):
        bbox = [self.__xmin-1, self.__ymin-1, self.__xmax+1, self.__ymax+1]
        fp.write("%!PS-Adobe-2.0 EPSF-1.2\n")
        fp.write("%%Title: " + self.title + "\n")
        fp.write("%%Creator: " + self.creator + "\n")
        if self.author:
            fp.write("%%Author: " + self.author + "\n")
        fp.write("%%CreationDate: " + self.creation_date + "\n")
        fp.write("%%DocumentFonts: " + " ".join(self.__font_ids.keys()) + "\n")
        fp.write("%%Pages: 1\n")

        bbox = theme.adjust_bounding_box(bbox)

        fp.write("%%%%BoundingBox: %d %d %d %d\n" % \
                 (round(xscale(bbox[0])),
                  round(yscale(bbox[1])),
                  round(xscale(bbox[2])),
                  round(yscale(bbox[3]))))
        fp.write("%%EndComments\n")
        if self.aux_comments != "":
            for line in self.aux_comments.split("\n"):
                fp.write("% " + line + "\n")

        fp.write(preamble_text)
        for name, id in self.__font_ids.items():
            fp.write("/%s {/%s findfont SF} def\n" % (id, name))
        fp.write("%%EndProlog\n%%Page: 1 1\n")


preamble_text="""
40 dict begin
/RECT {4 dict begin
  /y2 exch def
  /x2 exch def
  /y1 exch def
  /x1 exch def
  newpath x1 y1 moveto x2 y1 lineto x2 y2 lineto x1 y2 lineto closepath
  end
} def

/SF {exch scalefont setfont} def
/TB {matrix currentmatrix} def
/TE {setmatrix} def
/GB {matrix currentmatrix} def
/GE {setmatrix} def
/SG {1 1 1 setrgbcolor setgray} def
/SC {1 setgray setrgbcolor} def
/SL {[] 0 setdash setlinejoin setlinecap setlinewidth} def
/SLD {setdash setlinejoin setlinecap setlinewidth} def
/M {moveto} def
/L {lineto} def
/T {translate} def
/R {rotate} def
/N {newpath} def
/ST {stroke} def
/CP {closepath} def
/GR {grestore} def
/GS {gsave} def
"""

# SL: set line style.
# width [dash] x linecap linejoin SL -> 

# SF: set font.
# name size SF -> 

