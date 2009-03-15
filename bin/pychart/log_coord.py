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

class T(coord.T):
    def get_canvas_pos(self, size, val, min, max):
        if val <= 0:
            return 0
        xminl = math.log(min)
        xmaxl = math.log(max)
        vl = math.log(val)
        return size * (vl-xminl) / float(xmaxl-xminl)
    def get_tics(self, min, max, interval):
        "Generate the list of places for drawing tick marks."
        v = []
        if min <= 0:
            raise Exception, "Min value (%s) < 0 in a log coordinate." % min
        x = min
        while x <= max:
            v.append(x)
            x = x * interval
        return v
    def get_min_max(self, dmin, dmax, interval):
        interval = interval or 10
	dmin = max(0, dmin) # we can't have a negative value with a log scale.
        v = 1.0
        while v > dmin:
            v = v / interval
        dmin = v
        v = 1.0
        while v < dmax:
            v = v * interval
        dmax = v

        return dmin, dmax, interval
    
