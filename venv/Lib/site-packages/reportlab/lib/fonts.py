#!/bin/env python
#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/lib/fonts.py
__version__='3.3.0'
__doc__='''Utilities to associate bold and italic versions of fonts into families

Bold, italic and plain fonts are usually implemented in separate disk files;
but non-trivial apps want <b>this</b> to do the right thing.   We therefore
need to keep 'mappings' between the font family name and the right group
of up to 4 implementation fonts to use.

Most font-handling code lives in pdfbase, and this probably should too.

'''
###############################################################################
#   A place to put useful font stuff
###############################################################################
#
#      Font Mappings
# The brute force approach to finding the correct postscript font name;
# much safer than the rule-based ones we tried.
# preprocessor to reduce font face names to the shortest list
# possible.  Add any aliases you wish; it keeps looking up
# until it finds no more translations to do.  Any input
# will be lowercased before checking.
_family_alias = {
            'serif':'times',
            'sansserif':'helvetica',
            'monospaced':'courier',
            'arial':'helvetica'
            }
#maps a piddle font to a postscript one.
_tt2ps_map = {
            #face, bold, italic -> ps name
            ('times', 0, 0) :'Times-Roman',
            ('times', 1, 0) :'Times-Bold',
            ('times', 0, 1) :'Times-Italic',
            ('times', 1, 1) :'Times-BoldItalic',

            ('courier', 0, 0) :'Courier',
            ('courier', 1, 0) :'Courier-Bold',
            ('courier', 0, 1) :'Courier-Oblique',
            ('courier', 1, 1) :'Courier-BoldOblique',

            ('helvetica', 0, 0) :'Helvetica',
            ('helvetica', 1, 0) :'Helvetica-Bold',
            ('helvetica', 0, 1) :'Helvetica-Oblique',
            ('helvetica', 1, 1) :'Helvetica-BoldOblique',

            # there is only one Symbol font
            ('symbol', 0, 0) :'Symbol',
            ('symbol', 1, 0) :'Symbol',
            ('symbol', 0, 1) :'Symbol',
            ('symbol', 1, 1) :'Symbol',

            # ditto for dingbats
            ('zapfdingbats', 0, 0) :'ZapfDingbats',
            ('zapfdingbats', 1, 0) :'ZapfDingbats',
            ('zapfdingbats', 0, 1) :'ZapfDingbats',
            ('zapfdingbats', 1, 1) :'ZapfDingbats',
            }

_ps2tt_map={}
for k in sorted(_tt2ps_map.keys()):
    v = _tt2ps_map[k].lower()
    if v not in _ps2tt_map:
        _ps2tt_map[v] = k
    v = k[0].lower()
    if v not in _ps2tt_map:
        _ps2tt_map[v] = k

def ps2tt(psfn):
    'ps fontname to family name, bold, italic'
    psfn = psfn.lower()
    if psfn in _ps2tt_map:
        return _ps2tt_map[psfn]
    raise ValueError("Can't map determine family/bold/italic for %s" % psfn)

def tt2ps(fn,b,i):
    'family name + bold & italic to ps font name'
    K = (fn.lower(),b,i)
    if K in _tt2ps_map:
        return _tt2ps_map[K]
    else:
        fn, b1, i1 = ps2tt(K[0])
        K = fn, b1|b, i1|i
        if K in _tt2ps_map:
            return _tt2ps_map[K]
    raise ValueError("Can't find concrete font for family=%s, bold=%d, italic=%d" % (fn, b, i))

def addMapping(face, bold, italic, psname):
    'allow a custom font to be put in the mapping'
    k = face.lower(), bold, italic
    _tt2ps_map[k] = psname
    _ps2tt_map[psname.lower()] = k
