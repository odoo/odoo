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
import coord
import math
import pychart_util

class T(coord.T):
    def get_canvas_pos(self, size, val, min, max2):
        return size * (val - min) / max(float(max2 - min),0.01)

    def get_tics(self, min, max, interval):
        v = []
        x = min
        while x <= max:
            v.append(x)
            x += interval
        return v
    def get_min_max(self, dmin, dmax, interval):
        if not interval:
            if dmax == dmin:
                interval = 10
            else:
                interval = 10 ** (float(int(math.log(dmax-dmin)/math.log(10))))
        dmin = min(dmin, pychart_util.round_down(dmin, interval))
        dmax = max(dmax, pychart_util.round_up(dmax, interval) + interval/2.0)
        return dmin, dmax, interval
