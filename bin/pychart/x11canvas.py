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
import os
import gs_frontend
import theme
import sys

class T(gs_frontend.T):
    def close(self):
        gs_frontend.T.close(self)
        self.start_gs("-sDEVICE=x11")
        sys.stdin.readline()
        self.close_gs()

