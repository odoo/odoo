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
import os
import re
import getopt
import pychart_util

__doc__ = """This module is defines variables for changing the looks
of charts. All the variables can be changed either via environment
variable PYCHART_OPTIONS or via the command-line options.

The value of PYCHART_OPTIONS should be a sequence of var=val separated
by space.  Below is an example, which tells Pychart to write to file
foo.pdf and use Times-Roman as the default font.

PYCHART_OPTIONS="output=foo.pdf font-family=Times"

The summary of attributes that can be set via PYCHART_OPTIONS follows:

output=FILENAME (default: stdout)

    Set the output file name.
    
format=[ps|pdf|pdf-uncompressed|png|x11|svg] (default: ps)

    Set the output file format.
    
font-family=NAME (default: Helvetica)

    Set the default font to be used by texts.
    
font-size=N (default: 9)

    Set the default font to be used by texts.
line-width=X (default: 0.4)

    Set the default line width, in points.  See also
    pychart.line_style.

scale=X (default: 1.0)

    Set the scaling factor.  The default is 1.0. 

color=[yes|no] (default: no)

    If yes, Pychart colorizes default object attributes.

You can also set these variables by calling theme.get_options.
"""

use_color = 0
scale_factor = 1
output_format = None   # "ps", "pdf", "png", "x11", or "svg"
compress_output = 1
output_file = ""

default_font_family = "Helvetica"
default_font_size = 9
default_line_height = None
default_font_halign = "L"
default_font_valign = "B"
default_font_angle = 0
default_line_width = 0.4

debug_level = 1
delta_bounding_box = [-3, -3, 3, 3]
bounding_box = {}
         
def parse_yesno(str):
    if str in ("yes", "true", "1"):
        return 1
    else:
        return 0

def parse_bounding_box(arg):
    global delta_bounding_box, bounding_box
    
    l = arg.split(",")
    if len(l) != 4:
        raise ValueError, "Need to specify margin=LEFT,BOTTOM,RIGHT,TOP"
    for i in range(0, 4):
        val = l[i].strip()
        if val[0] == '+':
            delta_bounding_box[i] = int(val[1:])
        elif val[0] == '-':
            delta_bounding_box[i] = int(val[1:])
        else:
            bounding_box[i] = int(val)

def adjust_bounding_box(bbox):
    """Adjust the bounding box as specified by user.
    Returns the adjusted bounding box.

    - bbox: Bounding box computed from the canvas drawings.
    It must be a four-tuple of numbers.
    """
    for i in range(0, 4):
        if bounding_box.has_key(i):
            bbox[i] = bounding_box[i]
        else:
            bbox[i] += delta_bounding_box[i]
    return bbox

def parse_option(opt, arg):
    global use_color, scale_factor, margin
    global output_format, output_file, compress_output
    global default_font_family, default_font_size
    global default_line_height
    global default_line_width, debug_level
    if opt == "format":
        if arg in ("ps", "eps"):
            output_format = "ps"
        elif arg == "png":
            output_format = "png"
        elif arg == "svg":
            output_format = "svg"
        elif arg == "x11":
            output_format = "x11"
        elif arg == "pdf-uncompressed":
            output_format = "pdf"
            compress_output = 0
        elif arg in ("pdf-compressed", "pdf"):
            output_format = "pdf"
            compress_output = 1
        else:
            raise ValueError, "Unknown output option: " + str(arg)
    elif opt == "output":
        output_file = arg
    elif opt == "color":
        use_color = 1
    elif opt == "scale":
        scale_factor = float(arg)
    elif opt == "bbox":
        parse_bounding_box(arg)
    elif opt == "font-family":
        default_font_family = arg
    elif opt == "font-size":
        default_font_size = float(arg)
        default_line_height = float(arg)            
    elif opt == "line-width":
        default_line_width = float(arg)
    elif opt == "debug-level":
        debug_level = int(arg)
    else:
        raise getopt.GetoptError, "Unknown option: " + opt + " " + arg
    
if os.environ.has_key("PYCHART_OPTIONS"):
    for opt in os.environ["PYCHART_OPTIONS"].split():
        opt, arg = opt.split("=")
        parse_option(opt, arg)

hooks = []        
def add_reinitialization_hook(proc):
    global hooks
    hooks.append(proc)
    proc()
    
def usage():
    print "Usage: %s [options..]" % sys.argv[0]
    print """
    --scale=X: Set the scaling factor to X (default: 1.0).
    --format=[ps|png|pdf|x11|svg]: Set the output format (default: ps).
    --font-family=NAME: Set the default font family (default: Helvetica).
    --font-size=NAME: Set the default font size (default: 9pts).
    --line-width=NAME: Set the default line width (default: 0.4).
    --debug-level=N: Set the messaging verbosity (default: 0).
    --bbox=LEFT,BOTTOM,RIGHT,TOP: Specifies the amount of space (in PS points) to be left in the edges of the picture (default: -1,-1,+1,+1).
    """

def reinitialize():
    """This procedure must be called after setting variables in
    the |theme| module. This procedure propagates the new values of
    the theme variables to other modules that depend on their values."""
    for proc in hooks:
        proc()
    
def get_options(argv = None):
    """This procedure takes a list of command line arguments in <argv>
    and parses
    options. It returns the non-parsed portion of <argv>. Parameter
    <argv> can be
    omitted, in which case its value defaults to |sys.argv[1:]|.
    The options supported are: "|--format=[ps,png,pdf,x11,svg]|",
    "|--output=|<file>", "|--color=[yes,no]|"
    "|--scale=|<X>", "|--font-family=|<name>", "|--font-size=|<X>",
    "|--line-width=|<X>",
    "|--debug-level=|<N>", "|bbox=|<left,bottom,right,top>".
    The below code shows an example.

#!/usr/bin/python
from pychart import *
args = theme.get_options()
ar = area.T(...)
...
    """
    if argv == None:
        argv = sys.argv[1:]
    try:
        opts, args = getopt.getopt(argv, "d:co:f:",
                                   ["format=", "output=", "color=",
                                    "scale=", "font-family=", "font-size=",
                                    "line-width=", "debug-level=",
                                    "bbox="])
    except getopt.GetoptError, foo:
        print foo
        usage()
        raise getopt.GetoptError
    for opt, arg in opts:
        if opt == "-d":
            parse_option("debug-level", arg)
        elif opt == "-c":
            parse_option("color", None)
        elif opt == "-o":
            parse_option("output", arg)
        elif opt == "-f":
            parse_option("format", arg)
        else:
            parse_option(opt[2:], arg)
    reinitialize()
    return args

    
