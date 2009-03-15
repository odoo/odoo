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
import gs_frontend
import theme

class T(gs_frontend.T):
    def close(self):
        gs_frontend.T.close(self)
	if self.__output_lines == []:
	    return

        if theme.use_color:
            gs_args = "-sDEVICE=png256 -dTextAlphaBits=4 -q -dNOPAUSE" #PDS
        else:
            gs_args = "-sDEVICE=pnggray -dTextAlphaBits=4 -q -dNOPAUSE" #PDS

            
        temp_fname = None # the temporary file desc.
        out_fd = None  # the final destination. 
        
        if self.__out_fname and isinstance(self.__out_fname, str):
            gs_args += " -sOutputFile=%s" % self.__out_fname
        else:
            if not self.__out_fname:
                out_fd = sys.stdout
            else:
                if not hasattr(self.__out_fname, "write"):
                    raise Exception, "Expecting either a filename or a file-like object, but got %s" % self.__out_fname
                out_fd = self.__out_fname
            import tempfile
            temp_fname = tempfile.mktemp()
            gs_args += " -sOutputFile=%s" % temp_fname
        self.start_gs(gs_args)
        self.close_gs()

        if temp_fname:
            temp_fd = file(temp_fname, 'rb')
            out_fd.write(temp_fd.read())
            temp_fd.close()
            


