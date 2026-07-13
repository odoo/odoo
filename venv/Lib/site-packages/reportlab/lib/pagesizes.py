#!/bin/env python
#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/lib/pagesizes.py

"""This module defines a few common page sizes in points (1/72 inch).
To be expanded to include things like label sizes, envelope windows
etc."""
__version__='3.4.18'

from reportlab.lib.units import mm, inch

#ISO 216 standard paer sizes; see eg https://en.wikipedia.org/wiki/ISO_216
A0 = (841*mm,1189*mm)
A1 = (594*mm,841*mm)
A2 = (420*mm,594*mm)
A3 = (297*mm,420*mm)
A4 = (210*mm,297*mm)
A5 = (148*mm,210*mm)
A6 = (105*mm,148*mm)
A7 = (74*mm,105*mm)
A8 = (52*mm,74*mm)
A9 = (37*mm,52*mm)
A10 = (26*mm,37*mm)

B0 = (1000*mm,1414*mm)
B1 = (707*mm,1000*mm)
B2 = (500*mm,707*mm)
B3 = (353*mm,500*mm)
B4 = (250*mm,353*mm)
B5 = (176*mm,250*mm)
B6 = (125*mm,176*mm)
B7 = (88*mm,125*mm)
B8 = (62*mm,88*mm)
B9 = (44*mm,62*mm)
B10 = (31*mm,44*mm)

C0 = (917*mm,1297*mm)
C1 = (648*mm,917*mm)
C2 = (458*mm,648*mm)
C3 = (324*mm,458*mm)
C4 = (229*mm,324*mm)
C5 = (162*mm,229*mm)
C6 = (114*mm,162*mm)
C7 = (81*mm,114*mm)
C8 = (57*mm,81*mm)
C9 = (40*mm,57*mm)
C10 = (28*mm,40*mm)

#American paper sizes
LETTER = (8.5*inch, 11*inch)
LEGAL = (8.5*inch, 14*inch)
ELEVENSEVENTEEN = (11*inch, 17*inch)

# From https://en.wikipedia.org/wiki/Paper_size
JUNIOR_LEGAL = (5*inch, 8*inch)
HALF_LETTER = (5.5*inch, 8*inch)
GOV_LETTER = (8*inch, 10.5*inch)
GOV_LEGAL = (8.5*inch, 13*inch)
TABLOID = ELEVENSEVENTEEN
LEDGER = (17*inch, 11*inch)

# lower case is deprecated as of 12/2001, but here
# for compatability
letter=LETTER
legal=LEGAL
elevenSeventeen = ELEVENSEVENTEEN

#functions to mess with pagesizes
def landscape(pagesize):
    """Use this to get page orientation right"""
    a, b = pagesize
    if a < b:
        return (b, a)
    else:
        return (a, b)

def portrait(pagesize):
    """Use this to get page orientation right"""
    a, b = pagesize
    if a >= b:
        return (b, a)
    else:
        return (a, b)
