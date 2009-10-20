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
import pychart_util
import theme
import sys
import os
import os.path
import pscanvas
import tempfile
import string
import basecanvas
from scaling import *

def get_gs_path():
    """Guess where the Ghostscript executable is
    and return its absolute path name."""
    path = os.defpath
    if os.environ.has_key("PATH"):
        path = os.environ["PATH"]
    for dir in path.split(os.pathsep):
        for name in ("gs", "gs.exe", "gswin32c.exe"):
            g = os.path.join(dir, name)
            if os.path.exists(g):
                return g
    raise Exception, "Ghostscript not found."

class T(pscanvas.T):
    def __write_contents(self, fp):
        fp.write(pscanvas.preamble_text)
        for name, id in self.__font_ids.items():
            fp.write("/%s {/%s findfont SF} def\n" % (id, name))
        fp.write("%d %d translate\n" % (-self.bbox[0], -self.bbox[1]))
        fp.writelines(self.__output_lines)
        fp.write("showpage end\n")
        fp.flush()

    def close(self):
        # Don't call pscanvas.T.close, as it creates a
        # ps file. 
        basecanvas.T.close(self)
        
    def start_gs(self, arg):
        self.bbox = theme.adjust_bounding_box([xscale(self.__xmin),
                                               yscale(self.__ymin),
                                               xscale(self.__xmax),
                                               yscale(self.__ymax)])
        
        gs_path = get_gs_path()
        self.pipe_fp = None
	if self.__output_lines == []:
	    return

        if sys.platform != "win32" and hasattr(os, "popen"):
            # UNIX-like systems
            cmdline = "\"%s\" -q %s -g%dx%d -q >/dev/null 2>&1" % \
            (gs_path, arg,
             self.bbox[2] - self.bbox[0],
             self.bbox[3] - self.bbox[1])
            self.pipe_fp = os.popen(cmdline, "w")
            self.__write_contents(self.pipe_fp)
        else:
            # XXX should use mktemp, but need to support python<=2.2 as well.
            fname = tempfile.mktemp("xxx")
            fp = open(fname, "wb")
            self.__write_contents(fp)
            fp.close()
            cmdline = "\"%s\" -q %s -g%dx%d -q <%s >NUL" % \
            (gs_path, arg,
             self.bbox[2] - self.bbox[0],
             self.bbox[3] - self.bbox[1], fname)
            os.system(cmdline)
            os.unlink(fname)
    def close_gs(self):
        if self.pipe_fp:
            self.pipe_fp.close()
            self.pipe_fp = None
