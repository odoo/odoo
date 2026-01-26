#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/pdfbase/_fontdata.py
#$Header $
__version__='3.3.0'
__doc__="""Database of font related things

    - standardFonts - tuple of the 14 standard string font names
    - standardEncodings - tuple of the known standard font names
    - encodings - a mapping object from standard encoding names (and minor variants)
      to the encoding vectors ie the tuple of string glyph names
    - widthsByFontGlyph - fontname x glyphname --> width of glyph
    - widthVectorsByFont - fontName -> vector of widths 
    
    This module defines a static, large data structure.  At the request
    of the Jython project, we have split this off into separate modules
    as Jython cannot handle more than 64k of bytecode in the 'top level'
    code of a Python module.  
"""
import os, sys

# mapping of name to width vector, starts empty until fonts are added
# e.g. widths['Courier'] = [...600,600,600,...]
widthVectorsByFont = {}
fontsByName = {}
fontsByBaseEnc = {}
# this is a list of the standard 14 font names in Acrobat Reader
standardFonts = (
    'Courier', 'Courier-Bold', 'Courier-Oblique', 'Courier-BoldOblique',
    'Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique', 'Helvetica-BoldOblique',
    'Times-Roman', 'Times-Bold', 'Times-Italic', 'Times-BoldItalic',
    'Symbol','ZapfDingbats')

standardFontAttributes = {
    #family, bold, italic defined for basic ones
    'Courier':('Courier',0,0),
    'Courier-Bold':('Courier',1,0),
    'Courier-Oblique':('Courier',0,1),
    'Courier-BoldOblique':('Courier',1,1),
    
    'Helvetica':('Helvetica',0,0),
    'Helvetica-Bold':('Helvetica',1,0),
    'Helvetica-Oblique':('Helvetica',0,1),
    'Helvetica-BoldOblique':('Helvetica',1,1),

    'Times-Roman':('Times-Roman',0,0),
    'Times-Bold':('Times-Roman',1,0),
    'Times-Italic':('Times-Roman',0,1),
    'Times-BoldItalic':('Times-Roman',1,1),

    'Symbol':('Symbol',0,0),
    'ZapfDingbats':('ZapfDingbats',0,0)

    }

#this maps fontnames to the equivalent filename root.
_font2fnrMapWin32 = {
                    'symbol':                   'sy______',
                    'zapfdingbats':             'zd______',
                    'helvetica':                '_a______',
                    'helvetica-bold':           '_ab_____',
                    'helvetica-boldoblique':    '_abi____',
                    'helvetica-oblique':        '_ai_____',
                    'times-bold':               '_eb_____',
                    'times-bolditalic':         '_ebi____',
                    'times-italic':             '_ei_____',
                    'times-roman':              '_er_____',
                    'courier-bold':             'cob_____',
                    'courier-boldoblique':      'cobo____',
                    'courier':                  'com_____',
                    'courier-oblique':          'coo_____',
                    }
if sys.platform in ('linux2',):
    _font2fnrMapLinux2 ={
                'symbol': 'Symbol',
                'zapfdingbats': 'ZapfDingbats',
                'helvetica': 'Arial',
                'helvetica-bold': 'Arial-Bold',
                'helvetica-boldoblique': 'Arial-BoldItalic',
                'helvetica-oblique': 'Arial-Italic',
                'times-bold': 'TimesNewRoman-Bold',
                'times-bolditalic':'TimesNewRoman-BoldItalic',
                'times-italic': 'TimesNewRoman-Italic',
                'times-roman': 'TimesNewRoman',
                'courier-bold': 'Courier-Bold',
                'courier-boldoblique': 'Courier-BoldOblique',
                'courier': 'Courier',
                'courier-oblique': 'Courier-Oblique',
                }
    _font2fnrMap = _font2fnrMapLinux2
    for k, v in _font2fnrMap.items():
        if k in _font2fnrMapWin32.keys():
            _font2fnrMapWin32[v.lower()] = _font2fnrMapWin32[k]
    del k, v
else:
    _font2fnrMap = _font2fnrMapWin32

def _findFNR(fontName):
    return _font2fnrMap[fontName.lower()]

from reportlab.rl_config import T1SearchPath
from reportlab.lib.utils import rl_isfile
def _searchT1Dirs(n,rl_isfile=rl_isfile,T1SearchPath=T1SearchPath):
    assert T1SearchPath!=[], "No Type-1 font search path"
    for d in T1SearchPath:
        f = os.path.join(d,n)
        if rl_isfile(f): return f
    return None
del T1SearchPath, rl_isfile

def findT1File(fontName,ext='.pfb'):
    if sys.platform in ('linux2',) and ext=='.pfb':
        try:
            f = _searchT1Dirs(_findFNR(fontName))
            if f: return f
        except:
            pass

        try:
            f = _searchT1Dirs(_font2fnrMapWin32[fontName.lower()]+ext)
            if f: return f
        except:
            pass

    return _searchT1Dirs(_findFNR(fontName)+ext)

# this lists the predefined font encodings - WinAnsi and MacRoman.  We have
# not added MacExpert - it's possible, but would complicate life and nobody
# is asking.  StandardEncoding means something special.
standardEncodings = ('WinAnsiEncoding','MacRomanEncoding','StandardEncoding','SymbolEncoding','ZapfDingbatsEncoding','PDFDocEncoding', 'MacExpertEncoding')

#this is the global mapping of standard encodings to name vectors
class _Name2StandardEncodingMap(dict):
    '''Trivial fake dictionary with some [] magic'''
    _XMap = {'winansi':'WinAnsiEncoding','macroman': 'MacRomanEncoding','standard':'StandardEncoding','symbol':'SymbolEncoding', 'zapfdingbats':'ZapfDingbatsEncoding','pdfdoc':'PDFDocEncoding', 'macexpert':'MacExpertEncoding'}
    def __setitem__(self,x,v):
        y = x.lower()
        if y[-8:]=='encoding': y = y[:-8]
        y = self._XMap[y]
        if y in self: raise IndexError('Encoding %s is already set' % y)
        dict.__setitem__(self,y,v)

    def __getitem__(self,x):
        y = x.lower()
        if y[-8:]=='encoding': y = y[:-8]
        y = self._XMap[y]
        return dict.__getitem__(self,y)

encodings = _Name2StandardEncodingMap()

#due to compiled method size limits in Jython,
#we pull these in from separate modules to keep this module
#well under 64k.  We might well be able to ditch many of
#these anyway now we run on Unicode.

from reportlab.pdfbase._fontdata_enc_winansi import WinAnsiEncoding
from reportlab.pdfbase._fontdata_enc_macroman import MacRomanEncoding
from reportlab.pdfbase._fontdata_enc_standard import StandardEncoding
from reportlab.pdfbase._fontdata_enc_symbol import SymbolEncoding
from reportlab.pdfbase._fontdata_enc_zapfdingbats import ZapfDingbatsEncoding
from reportlab.pdfbase._fontdata_enc_pdfdoc import PDFDocEncoding
from reportlab.pdfbase._fontdata_enc_macexpert import MacExpertEncoding
encodings.update({
    'WinAnsiEncoding': WinAnsiEncoding,
    'MacRomanEncoding': MacRomanEncoding,
    'StandardEncoding': StandardEncoding,
    'SymbolEncoding': SymbolEncoding,
    'ZapfDingbatsEncoding': ZapfDingbatsEncoding,
    'PDFDocEncoding': PDFDocEncoding,
    'MacExpertEncoding': MacExpertEncoding,
})

ascent_descent = {
    'Courier': (629, -157),
    'Courier-Bold': (626, -142),
    'Courier-BoldOblique': (626, -142),
    'Courier-Oblique': (629, -157),
    'Helvetica': (718, -207),
    'Helvetica-Bold': (718, -207),
    'Helvetica-BoldOblique': (718, -207),
    'Helvetica-Oblique': (718, -207),
    'Times-Roman': (683, -217),
    'Times-Bold': (676, -205),
    'Times-BoldItalic': (699, -205),
    'Times-Italic': (683, -205),
    'Symbol': (0, 0),
    'ZapfDingbats': (0, 0)
    }

# ditto about 64k limit - profusion of external files
import reportlab.pdfbase._fontdata_widths_courier
import reportlab.pdfbase._fontdata_widths_courierbold
import reportlab.pdfbase._fontdata_widths_courieroblique
import reportlab.pdfbase._fontdata_widths_courierboldoblique
import reportlab.pdfbase._fontdata_widths_helvetica
import reportlab.pdfbase._fontdata_widths_helveticabold
import reportlab.pdfbase._fontdata_widths_helveticaoblique
import reportlab.pdfbase._fontdata_widths_helveticaboldoblique
import reportlab.pdfbase._fontdata_widths_timesroman
import reportlab.pdfbase._fontdata_widths_timesbold
import reportlab.pdfbase._fontdata_widths_timesitalic
import reportlab.pdfbase._fontdata_widths_timesbolditalic
import reportlab.pdfbase._fontdata_widths_symbol
import reportlab.pdfbase._fontdata_widths_zapfdingbats
widthsByFontGlyph = {
    'Courier':
    reportlab.pdfbase._fontdata_widths_courier.widths,
    'Courier-Bold':
    reportlab.pdfbase._fontdata_widths_courierbold.widths,
    'Courier-Oblique':
    reportlab.pdfbase._fontdata_widths_courieroblique.widths,
    'Courier-BoldOblique':
    reportlab.pdfbase._fontdata_widths_courierboldoblique.widths,
    'Helvetica':
    reportlab.pdfbase._fontdata_widths_helvetica.widths,
    'Helvetica-Bold':
    reportlab.pdfbase._fontdata_widths_helveticabold.widths,
    'Helvetica-Oblique':
    reportlab.pdfbase._fontdata_widths_helveticaoblique.widths,
    'Helvetica-BoldOblique':
    reportlab.pdfbase._fontdata_widths_helveticaboldoblique.widths,
    'Times-Roman':
    reportlab.pdfbase._fontdata_widths_timesroman.widths,
    'Times-Bold':
    reportlab.pdfbase._fontdata_widths_timesbold.widths,
    'Times-Italic':
    reportlab.pdfbase._fontdata_widths_timesitalic.widths,
    'Times-BoldItalic':
    reportlab.pdfbase._fontdata_widths_timesbolditalic.widths,
    'Symbol':
    reportlab.pdfbase._fontdata_widths_symbol.widths,
    'ZapfDingbats':
    reportlab.pdfbase._fontdata_widths_zapfdingbats.widths,
}


#preserve the initial values here
def _reset(
        initial_dicts=dict(
            ascent_descent=ascent_descent.copy(),
            fontsByBaseEnc=fontsByBaseEnc.copy(),
            fontsByName=fontsByName.copy(),
            standardFontAttributes=standardFontAttributes.copy(),
            widthVectorsByFont=widthVectorsByFont.copy(),
            widthsByFontGlyph=widthsByFontGlyph.copy(),
            )
        ):
    for k,v in initial_dicts.items():
        d=globals()[k]
        d.clear()
        d.update(v)

from reportlab.rl_config import register_reset
register_reset(_reset)
del register_reset
