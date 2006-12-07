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
import theme

x_base = 300
y_base = 300

def xscale(x):
    return x * theme.scale_factor + x_base
def yscale(y):
    return y * theme.scale_factor + y_base

def nscale(x):
    return x * theme.scale_factor
def nscale_seq(x):
    return map(nscale, x)

