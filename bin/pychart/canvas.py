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
import basecanvas
import pscanvas
import pdfcanvas
import svgcanvas
import pngcanvas
import x11canvas
import theme
import re

invalid_coord = -999999
_oldexitfunc = None

T = basecanvas.T

def init(fname = None, format = None):

    """This is a "factory" procedure that creates a new canvas.T object.
    Both parameters, <fname> and
    <format>, are optional. Parameter <fname> specifies either the output
    file name or a file object. Parameter <format>, if specified, defines the
    file's format. Its value must be one of "ps", "pdf", "svg", "x11", or
    "png".

    When <fname> is omitted or is None, the output is sent to standard
    output. When <format> is omitted, it is guessed from the <fname>'s
    suffix; failing that, "ps" is selected."""
    
    fname = fname or theme.output_file
    format = format or theme.output_format
    
    if format == None:
        if not isinstance(fname, str):
            format = "ps"
        elif re.search("pdf$", fname):
            format = "pdf"
        elif re.search("png$", fname):
            format = "png"
        elif re.search("svg$", fname):
            format = "svg"
        else:
            format = "ps"

    if format == "ps":
        can = pscanvas.T(fname)
    elif format == "png":
        can = pngcanvas.T(fname)
    elif format == "x11":
        can = x11canvas.T(fname)
    elif format == "svg":               
        can = svgcanvas.T(fname)
    else:
        can = pdfcanvas.T(fname, theme.compress_output)
    return can

def default_canvas():
    if len(basecanvas.active_canvases) > 0:
        return basecanvas.active_canvases[0]
    else:
        return init(None)

def _exit():
    global _oldexitfunc, _active_canvases
    
    for can in basecanvas.active_canvases[:]:
        can.close()
        
    if _oldexitfunc:
        foo = _oldexitfunc
        _oldexitfunc = None
        foo()

#
# The following procedures are there just for backward compatibility.
# 
def line(style, x1, y1, x2, y2):
    default_canvas().line(style, x1, y1, x2, y2)
def curve(style, points):
    default_canvas().curve(style, points)
def clip(x1, y1, x2, y2):
    default_canvas().clip(x1, y1, x2, y2)
def endclip():
    default_canvas().endclip()
def clip_polygon(points):
    default_canvas().clip_polygon(points)
def clip_ellipsis(x, y, radius, ratio = 1.0):
    default_canvas().clip_ellipsis(x, y, radius, ratio)
def ellipsis(line_style, pattern, x, y, radius, ratio = 1.0,
             start_angle=0, end_angle=360, shadow=None):
    default_canvas().ellipsis(line_style, pattern, x, y, radius, ratio,
                              start_angle, end_angle, shadow)
def rectangle(edge_style, pat, x1, y1, x2, y2, shadow = None):
    default_canvas().rectangle(edge_style, pat, x1, y1, x2, y2, shadow)
def polygon(edge_style, pat, points, shadow = None):
    default_canvas().polygon(edge_style, pat, points, shadow = None)
def close():
    default_canvas().close()
def round_rectangle(style, fill, x1, y1, x2, y2, radius, shadow=None):
    default_canvas().round_rectangle(style, fill, x1, y1, x2, y2, radius, shadow)
def show(x, y, str):
    default_canvas().show(x, y, str)
    

if not vars(sys).has_key("exitfunc"):
    sys.exitfunc = _exit
elif sys.exitfunc != _exit:
    _oldexitfunc = sys.exitfunc
    sys.exitfunc = _exit

#theme.add_reinitialization_hook(lambda: init(None))
