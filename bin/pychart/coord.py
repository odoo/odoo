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
class T(object):
    def get_canvas_pos(self, size, val, min, max):
        """
        Compute the screen location at which a sample value would be drawn.
        ``size`` is the width or height of the chart, in points.
        ``val`` is the sample value.
        ``min`` and ``max`` are the minimum and maximum sample values that
        are to be displayed over the length of ``size``.

        For example, suppose the width of a chart is 200 points and the
        minimum and maximum X values in the sample data are 100 and 150
        respectively. When Pychart wants to draw a sample point at the X
        value of 120, it will call
        area.T.x_coord.get_canvas_pos(size = 200, val = 120, min = 100, max = 150).
        """
        raise Exception
    
    def get_tics(self, min, max, interval):
        """Generate the list of places for drawing tick marks."""
        raise Exception
    
    def get_min_max(self, min, max, interval):
        """Compute the min/max values to be displayed in the chart.
        Parameters ``min`` and ``max`` are the minimum and maximum values
        of the sample data passed to the plots. Parameter ``interval`` is
        the value of attribute area.T.x_grid_interval (or y_grid_interval).
        It is None if these attributes are non-specified.

        This method must return tuple (dmin, dmax, dinterval).
        dmin should be ``min`` rounded down to some good number.
        dmax should be ``max`` rounded up to some good number.
        dinterval should be ``interval`` if it is non-None. Otherwise, the
        method must compute some good value.
        """
        
        raise Exception
