#!/bin/env python
#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/lib/units.py
__version__='3.3.0'
__doc__='''Defines inch, cm, mm etc as multiples of a point

You can now in user-friendly units by doing::

    from reportlab.lib.units import inch
    r = Rect(0, 0, 3 * inch, 6 * inch)

'''
inch = 72.0
cm = inch / 2.54
mm = cm * 0.1
pica = 12.0

def toLength(s):
    '''convert a string to  a length'''
    try:
        if s[-2:]=='cm': return float(s[:-2])*cm
        if s[-2:]=='in': return float(s[:-2])*inch
        if s[-2:]=='pt': return float(s[:-2])
        if s[-1:]=='i': return float(s[:-1])*inch
        if s[-2:]=='mm': return float(s[:-2])*mm
        if s[-4:]=='pica': return float(s[:-4])*pica
        return float(s)
    except:
        raise ValueError("Can't convert '%s' to length" % s)
