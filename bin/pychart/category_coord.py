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
import canvas

class T(coord.T):
    def __init__(self, data, col):

        """This attribute is meaningful only when x_coord_system ==
        'category'. This attribute selects the column of
        'x_category_data' from which X values are computed.
        Meaningful only when x_coord_system == 'category'.  This
        attribute specifies the data-set from which the X values are
        extracted. See also x_category_col."""
        
        self.data = data
        self.col = col
        
    def get_canvas_pos(self, size, val, min, max):
        i = 0.5
        for v in self.data:
            if v[self.col] == val:
                return size * i / float(len(self.data))
            i += 1
        # the drawing area is clipped. So negative offset will make this plot
        # invisible.
        return canvas.invalid_coord;
    def get_tics(self, min, max, interval):
        tics = []
        if interval == None: interval = 1
        
        for i in range(0, len(self.data), interval):
            tics.append(self.data[i][self.col])
        return tics    
        #return map(lambda pair, self = self: pair[self.col], self.data)

