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
import math
import sys
import time
import re

import font
import pychart_util
import version
from scaling import *

def _compute_bounding_box(points):
    """Given the list of coordinates (x,y), this procedure computes
    the smallest rectangle that covers all the points."""
    (xmin, ymin, xmax, ymax) = (999999, 999999, -999999, -999999)
    for p in points:
        xmin = min(xmin, p[0])
        xmax = max(xmax, p[0])
        ymin = min(ymin, p[1])
        ymax = max(ymax, p[1])
    return (xmin, ymin, xmax, ymax)

def _intersect_box(b1, b2):
    xmin = max(b1[0], b2[0])
    ymin = max(b1[1], b2[1])
    xmax = min(b1[2], b2[2])
    ymax = min(b1[3], b2[3])
    return (xmin, ymin, xmax, ymax)

def invisible_p(x, y):
    """Return true if the point (X, Y) is visible in the canvas."""
    if x < -499999 or y < -499999:
        return 1
    return 0

def to_radian(deg):
    return deg*2*math.pi / 360.0

def midpoint(p1, p2):
    return ( (p1[0]+p2[0])/2.0, (p1[1]+p2[1])/2.0 )


active_canvases = []

InvalidCoord = 999999
class T(object):
    def __init__(self):
        global active_canvases
        
        self.__xmax = -InvalidCoord
        self.__xmin = InvalidCoord
        self.__ymax = -InvalidCoord
        self.__ymin = InvalidCoord
        self.__clip_box = (-InvalidCoord, -InvalidCoord, InvalidCoord, InvalidCoord)
        self.__clip_stack = []
        self.__nr_gsave = 0
        
        self.title = re.sub("(.*)\\.py$", "\\1", sys.argv[0])
        self.creator = "pychart %s" % (version.version,)
        self.creation_date = time.strftime("(%m/%d/%y) (%I:%M %p)")
        self.aux_comments = ""
        self.author = None
        active_canvases.append(self)

    def set_title(self, s):
        """Define the string to shown in EPS/PDF "Title" field. The default value is the name of the script that creates the EPS/PDF file."""
        self.title = s
        
    def set_creator(self, tag):
        """Define the string to be shown in EPS %%Creator or PDF Producer field. The default value is "pychart"."""
        self.creator = tag
        
    def set_creation_date(self, s):
        """Define the string to shown in EPS/PDF "CreationDate" field. Defalt value of this field is the current time."""
        self.creation_date = s
        
    def set_author(self, s):
        """Set the author string. Unless this method is called, the Author field is not output in EPS or PDF."""
        self.author = s
        
    def add_aux_comments(self, s):
        """Define an auxiliary comments to be output to the file, just after the required headers"""
        self.aux_comments += s
        
    def close(self):
        """This method closes the canvas and writes
        contents to the associated file.
        Calling this procedure is optional, because
        Pychart calls this procedure for every open canvas on normal exit."""
        for i in range(0, len(active_canvases)):
            if active_canvases[i] == self:
                del active_canvases[i]
                return

    def open_output(self, fname):
        """Open the output file FNAME. Returns tuple (FD, NEED_CLOSE),
        where FD is a file (or file-like) object, and NEED_CLOSE is a
        boolean flag that tells whether FD.close() should be called
        after finishing writing to the file.
        
        FNAME can be one of the three things:
        (1) None, in which case (sys.stdout, False) is returned.
        (2) A file-like object, in which case (fname, False) is returned.
        (3) A string, in which case this procedure opens the file and returns
        (fd, True)."""

        if not fname:
            return (sys.stdout, False)
        elif isinstance(fname, str):
            return (file(fname, "wb"), True)
        else:
            if not hasattr(fname, "write"):
                raise Exception, "Expecting either a filename or a file-like object, but got %s" % fname
            return (fname, False)
        
    def setbb(self, x, y):
        """Call this method when point (X,Y) is to be drawn in the
        canvas. This methods expands the bounding box to include
        this point.""" 
        self.__xmin = min(self.__xmin, max(x, self.__clip_box[0]))
        self.__xmax = max(self.__xmax, min(x, self.__clip_box[2]))
        self.__ymin = min(self.__ymin, max(y, self.__clip_box[1]))
        self.__ymax = max(self.__ymax, min(y, self.__clip_box[3]))

    def fill_with_pattern(self, pat, x1, y1, x2, y2):
        if invisible_p(x2, y2): return
	
        self.comment("FILL pat=%s (%d %d)-(%d %d)\n" % (pat, x1, y1, x2, y2))
        self.set_fill_color(pat.bgcolor)
        self._path_polygon([(x1, y1), (x1, y2), (x2, y2), (x2, y1)])
        self.fill()
        pat.draw(self, x1, y1, x2, y2)
        self.comment("end FILL.\n")

    def _path_polygon(self, points):
        "Low-level polygon-drawing routine."
        (xmin, ymin, xmax, ymax) = _compute_bounding_box(points)
        if invisible_p(xmax, ymax):
            return
        self.setbb(xmin, ymin)
        self.setbb(xmax, ymax)
        
        self.newpath()
        self.moveto(xscale(points[0][0]), yscale(points[0][1]))
        for point in points[1:]:
            self.lineto(xscale(point[0]), yscale(point[1]))
        self.closepath()

    def polygon(self, edge_style, pat, points, shadow = None):
        """Draw a polygon with EDGE_STYLE, fill with PAT, and the edges
        POINTS. POINTS is a sequence of coordinates, e.g., ((10,10), (15,5),
        (20,8)). SHADOW is either None or a tuple (XDELTA, YDELTA,
        fillstyle). If non-null, a shadow of FILLSTYLE is drawn beneath
        the polygon at the offset of (XDELTA, YDELTA)."""

        if pat:
            self.comment("POLYGON points=[%s] pat=[%s]"
                        % (str(points), str(pat)))
            (xmin, ymin, xmax, ymax) = _compute_bounding_box(points)

            if shadow:
                xoff, yoff, shadow_pat = shadow
                self.gsave()
                self._path_polygon(map(lambda p, xoff=xoff, yoff=yoff: (p[0]+xoff, p[1]+yoff), points))
                self.clip_sub()
                self.fill_with_pattern(shadow_pat, xmin+xoff, ymin+yoff,
                                       xmax+xoff, ymax+yoff)
                self.grestore()

            self.gsave()
            self._path_polygon(points)
            self.clip_sub()
            self.fill_with_pattern(pat, xmin, ymin, xmax, ymax)
            self.grestore()
        if edge_style:
            self.comment("POLYGON points=[%s] edge=[%s]"
                         % (str(points), str(edge_style)))
            self.set_line_style(edge_style)
            self._path_polygon(points)
            self.stroke()
		
    def set_background(self, pat, x1, y1, x2, y2):
        xmax, xmin, ymax, ymin = self.__xmax, self.__xmin, self.__ymax, self.__ymin
        self.rectangle(None, pat, x1, y1, x2, y2)
        self.__xmax, self.__xmin, self.__ymax, self.__ymin = xmax, xmin, ymax, ymin 
        
    def rectangle(self, edge_style, pat, x1, y1, x2, y2, shadow = None):
        """Draw a rectangle with EDGE_STYLE, fill with PAT, and the
        bounding box (X1, Y1, X2, Y2).  SHADOW is either None or a
        tuple (XDELTA, YDELTA, fillstyle). If non-null, a shadow of
        FILLSTYLE is drawn beneath the polygon at the offset of
        (XDELTA, YDELTA)."""
        
        self.polygon(edge_style, pat, [(x1,y1), (x1,y2), (x2,y2), (x2, y1)],
                     shadow)

    def _path_ellipsis(self, x, y, radius, ratio, start_angle, end_angle):
        self.setbb(x - radius, y - radius*ratio)
        self.setbb(x + radius, y + radius*ratio)
        oradius = nscale(radius)
        centerx, centery = xscale(x), yscale(y)
        startx, starty = centerx+oradius * math.cos(to_radian(start_angle)), \
                         centery+oradius * math.sin(to_radian(start_angle))
        self.moveto(centerx, centery)
        if start_angle % 360 != end_angle % 360:
            self.moveto(centerx, centery)
            self.lineto(startx, starty)
        else:
            self.moveto(startx, starty)
        self.path_arc(xscale(x), yscale(y), nscale(radius),
                     ratio, start_angle, end_angle)
        self.closepath()

    def ellipsis(self, line_style, pattern, x, y, radius, ratio = 1.0,
                 start_angle=0, end_angle=360, shadow=None):
        """Draw an ellipsis with line_style and fill PATTERN. The center is \
        (X, Y), X radius is RADIUS, and Y radius is RADIUS*RATIO, whose \
        default value is 1.0. SHADOW is either None or a tuple (XDELTA,
        YDELTA, fillstyle). If non-null, a shadow of FILLSTYLE is drawn
        beneath the polygon at the offset of (XDELTA, YDELTA)."""

        if invisible_p(x + radius, y + radius*ratio):
            return

        if pattern:
            if shadow:
                x_off, y_off, shadow_pat = shadow
                self.gsave()
                self.newpath()
                self._path_ellipsis(x+x_off, y+y_off, radius, ratio,
                                    start_angle, end_angle)
                self.clip_sub()
                self.fill_with_pattern(shadow_pat,
                                       x-radius*2+x_off,
                                       y-radius*ratio*2+y_off,
                                       x+radius*2+x_off,
                                       y+radius*ratio*2+y_off)
                self.grestore()
            self.gsave()
            self.newpath()		
            self._path_ellipsis(x, y, radius, ratio, start_angle, end_angle)
            self.clip_sub()
            self.fill_with_pattern(pattern,
                                   (x-radius*2), (y-radius*ratio*2),
                                   (x+radius*2), (y+radius*ratio*2))
            self.grestore()
        if line_style:
            self.set_line_style(line_style)
            self.newpath()
            self._path_ellipsis(x, y, radius, ratio, start_angle, end_angle)
            self.stroke()

    def clip_ellipsis(self, x, y, radius, ratio = 1.0):
        """Create an elliptical clip region. You must call endclip() after
        you completed drawing. See also the ellipsis method."""

        self.gsave()
        self.newpath()
        self.moveto(xscale(x)+nscale(radius), yscale(y))
        self.path_arc(xscale(x), yscale(y), nscale(radius), ratio, 0, 360)
        self.closepath()
        self.__clip_stack.append(self.__clip_box)
        self.clip_sub()
	
    def clip_polygon(self, points):
        """Create a polygonal clip region. You must call endclip() after
        you completed drawing. See also the polygon method."""
        self.gsave()
        self._path_polygon(points)
        self.__clip_stack.append(self.__clip_box)
        self.__clip_box = _intersect_box(self.__clip_box, _compute_bounding_box(points))
        self.clip_sub()
		
    def clip(self, x1, y1, x2, y2):
        """Activate a rectangular clip region, (X1, Y1) - (X2, Y2).
        You must call endclip() after you completed drawing.
        
canvas.clip(x,y,x2,y2)
draw something ...
canvas.endclip()
"""
    
        self.__clip_stack.append(self.__clip_box)
        self.__clip_box = _intersect_box(self.__clip_box, (x1, y1, x2, y2))
        self.gsave()
        self.newpath()
        self.moveto(xscale(x1), yscale(y1))
        self.lineto(xscale(x1), yscale(y2))
        self.lineto(xscale(x2), yscale(y2))
        self.lineto(xscale(x2), yscale(y1))
        self.closepath()
        self.clip_sub()
	
    def endclip(self):
        """End the current clip region. When clip calls are nested, it
        ends the most recently created crip region."""
        self.__clip_box = self.__clip_stack[-1]
        del self.__clip_stack[-1]
        self.grestore()

    def curve(self, style, points):
        for p in points:
            self.setbb(p[0], p[1])
        self.newpath()
        self.set_line_style(style)
        self.moveto(xscale(points[0][0]), xscale(points[0][1]))
        i = 1
        n = 1
        while i < len(points):
            if n == 1:
                x2 = points[i]
                n += 1
            elif n == 2:
                x3 = points[i]
                n += 1
            elif n == 3:
                x4 = midpoint(x3, points[i])
                self.curveto(xscale(x2[0]), xscale(x2[1]),
                            xscale(x3[0]), xscale(x3[1]),
                            xscale(x4[0]), xscale(x4[1]))
                n = 1
            i += 1
            if n == 1:
                pass
            if n == 2:
                self.lineto(xscale(x2[0]), xscale(x2[1]))
            if n == 3:
                self.curveto(xscale(x2[0]), xscale(x2[1]),
                            xscale(x2[0]), xscale(x2[1]),
                            xscale(x3[0]), xscale(x3[1]))
            self.stroke()
		
    def line(self, style, x1, y1, x2, y2):
        if not style:
            return
        if invisible_p(x2, y2) and invisible_p(x1, y1):
            return

        self.setbb(x1, y1)
        self.setbb(x2, y2)

        self.newpath()
        self.set_line_style(style)
        self.moveto(xscale(x1), yscale(y1))
        self.lineto(xscale(x2), yscale(y2))
        self.stroke()

    def lines(self, style, segments):
        if not style:
            return
        (xmin, ymin, xmax, ymax) = _compute_bounding_box(segments)
        if invisible_p(xmax, ymax):
            return

        self.setbb(xmin, ymin)
        self.setbb(xmax, ymax)
        self.newpath()
        self.set_line_style(style)
        self.moveto(xscale(segments[0][0]), xscale(segments[0][1]))
        for i in range(1, len(segments)):
            self.lineto(xscale(segments[i][0]), yscale(segments[i][1]))
        self.stroke()

    def _path_round_rectangle(self, x1, y1, x2, y2, radius):
        self.moveto(xscale(x1 + radius), yscale(y1))
        self.lineto(xscale(x2 - radius), yscale(y1))
        self.path_arc(xscale(x2-radius), yscale(y1+radius), nscale(radius), 1, 270, 360)
        self.lineto(xscale(x2), yscale(y2-radius))
        self.path_arc(xscale(x2-radius), yscale(y2-radius), nscale(radius), 1, 0, 90)
        self.lineto(xscale(x1+radius), yscale(y2))
        self.path_arc(xscale(x1 + radius), yscale(y2 - radius), nscale(radius), 1, 90, 180)
        self.lineto(xscale(x1), xscale(y1+radius))
        self.path_arc(xscale(x1 + radius), yscale(y1 + radius), nscale(radius), 1, 180, 270)
	
    def round_rectangle(self, style, fill, x1, y1, x2, y2, radius, shadow=None):
        """Draw a rectangle with rounded four corners. Parameter <radius> specifies the radius of each corner."""

        if invisible_p(x2, y2):
            return
        self.setbb(x1, y1)
        self.setbb(x2, y2)

        if fill:
            if shadow:
                x_off, y_off, shadow_fill = shadow
                self.gsave();
                self.newpath()
                self._path_round_rectangle(x1+x_off, y1+y_off, x2+x_off, y2+y_off,
                                           radius)
                self.closepath()
                self.clip_sub()
                self.fill_with_pattern(shadow_fill, x1+x_off, y1+y_off,
                                       x2+x_off, y2+y_off)
                self.grestore()

            self.gsave();
            self.newpath()
            self._path_round_rectangle(x1, y1, x2, y2, radius)
            self.closepath()
            self.clip_sub()
            self.fill_with_pattern(fill, x1, y1, x2, y2)
            self.grestore()
        if style:
            self.set_line_style(style)
            self.newpath()
            self._path_round_rectangle(x1, y1, x2, y2, radius)
            self.closepath()
            self.stroke()

    def show(self, x, y, str):
        global out
        y_org = y
        org_str = str

        if invisible_p(x, y):
            return

        (xmin, xmax, ymin, ymax) = font.get_dimension(str)

        # rectangle(line_style.default, None, x+xmin, y+ymin, x+xmax, y+ymax)
        # ellipsis(line_style.default, None, x, y, 1)
        self.setbb(x+xmin, y+ymin)
        self.setbb(x+xmax, y+ymax)

        (halign, valign, angle) = font.get_align(str)

        base_x = x
        base_y = y

        # Handle vertical alignment
        if valign == "B":
            y = font.unaligned_text_height(str)
        elif valign == "T":
            y = 0
        elif valign == "M":
            y = font.unaligned_text_height(str) / 2.0

        (xmin, xmax, ymin, ymax) = font.get_dimension(org_str)
        # print org_str, xmin, xmax, ymin, ymax, x, y_org, y
        self.setbb(x+xmin, y_org+y+ymin)
        self.setbb(x+xmax, y_org+y+ymax)
        itr = font.text_iterator(None)

        max_width = 0

        lines = []
        for line in str.split('\n'):
            cur_width = 0
            cur_height = 0

            itr.reset(line)

            strs = []

            while 1:
                elem = itr.next()
                if not elem:
                    break

                (font_name, size, line_height, color, _h, _v, _a, str) = elem
                cur_width += font.line_width(font_name, size, str)
                max_width = max(cur_width, max_width)
                cur_height = max(cur_height, line_height)

                # replace '(' -> '\(', ')' -> '\)' to make
                # Postscript string parser happy.
                str = str.replace("(", "\\(")
                str = str.replace(")", "\\)")
                strs.append((font_name, size, color, str))
            lines.append((cur_width, cur_height, strs))

        for line in lines:
            cur_width, cur_height, strs = line
            cur_y = y - cur_height
            y = y - cur_height
            self.comment("cury: %d hei %d str %s\n" % (cur_y, cur_height, strs))
            if halign == 'C':
                cur_x = -cur_width/2.0
            elif halign == 'R':
                cur_x = -cur_width
            else:
                cur_x = 0

            rel_x, rel_y = pychart_util.rotate(cur_x, cur_y, angle)
            self.text_begin()
            self.text_moveto(xscale(base_x + rel_x),
                            yscale(base_y + rel_y), angle)
            for segment in strs:
                font_name, size, color, str = segment
                self.text_show(font_name, nscale(size), color, str)
            self.text_end()


