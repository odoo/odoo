# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pychart import color

colorline = [color.T(r=((r+3) % 11)/10.0,
                     g=((g+6) % 11)/10.0,
                     b=((b+9) % 11)/10.0)
             for r in range(11) for g in range(11) for b in range(11)]

def choice_colors(n):
    if n:
        return colorline[0:-1:len(colorline)/n]
    return []

if __name__=='__main__':
    print choice_colors(10)
