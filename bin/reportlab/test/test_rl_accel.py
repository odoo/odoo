__version__=''' $Id'''
__doc__='''basic tests.'''

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, printLocation

def getrc(defns,depth=1):
    from sys import getrefcount, _getframe
    f = _getframe(depth)
    G0 = f.f_globals
    L = f.f_locals
    if L is not G0:
        LL = [L]
        while 1:
            f = f.f_back
            G = f.f_globals
            L = f.f_locals
            if G is not G0 or G is L: break
            LL.append(L)
        L = {}
        for l in reversed(LL):
            L.update(l)
    else:
        L = L.copy()
    G0 = G0.copy()
    return [getrefcount(eval(x,L,G0))-1 for x in defns.split()]

def checkrc(defns,rcv0):
    rcv1 = getrc(defns,2)
    return ' '.join(["%s %d-->%d" % (x,v,w) for x,v,w in zip(defns.split(),rcv0,rcv1) if v!=w])

class RlAccelTestCase(unittest.TestCase):

    def testFpStr(self):
        # should give siz decimal places if less than 1.
        # if more, give up to seven sig figs
        from _rl_accel import fp_str
        assert fp_str(1,2,3)=='1 2 3'
        assert fp_str(1) == '1'

        assert fp_str(595.275574) == '595.2756'
        assert fp_str(59.5275574) == '59.52756'
        assert fp_str(5.95275574) == '5.952756'

    def test_AsciiBase85Encode(self):
        from _rl_accel import _AsciiBase85Encode
        assert _AsciiBase85Encode('Dragan Andric')=='6ul^K@;[2RDIdd%@f~>'

    def test_AsciiBase85Decode(self):
        from _rl_accel import _AsciiBase85Decode
        assert _AsciiBase85Decode('6ul^K@;[2RDIdd%@f~>')=='Dragan Andric'

    def testEscapePDF(self):
        from _rl_accel import escapePDF
        assert escapePDF('(test)')=='\\(test\\)'

    def test_instanceEscapePDF(self):
        from _rl_accel import _instanceEscapePDF
        assert _instanceEscapePDF('', '(test)')=='\\(test\\)'

    def testCalcChecksum(self):
        from _rl_accel import calcChecksum
        assert calcChecksum('test')==1952805748

    def testStringWidth(self):
        from _rl_accel import stringWidthU
        from reportlab.pdfbase.pdfmetrics import _py_stringWidth, getFont, registerFont, _fonts 
        from reportlab.pdfbase.ttfonts import TTFont
        ttfn = 'Luxi-Serif'
        t1fn = 'Times-Roman'
        registerFont(TTFont(ttfn, "luxiserif.ttf"))
        ttf = getFont(ttfn)
        t1f = getFont(t1fn)
        testCp1252 = 'copyright %s trademark %s registered %s ReportLab! Ol%s!' % (chr(169), chr(153),chr(174), chr(0xe9))
        enc='cp1252'
        senc = 'utf8'
        intern(senc)
        ts = 'ABCDEF\xce\x91\xce\xb2G'
        utext = 'ABCDEF\xce\x91\xce\xb2G'.decode('utf8')
        fontSize = 12
        defns="ttfn t1fn ttf t1f testCp1252 enc senc ts utext fontSize ttf.face ttf.face.charWidths ttf.face.defaultWidth t1f.widths t1f.encName t1f.substitutionFonts _fonts"
        rcv = getrc(defns)
        def tfunc(ts,fn,fontSize,enc):
            w1 = stringWidthU(ts,fn,fontSize,enc)
            w2 = _py_stringWidth(ts,fn,fontSize,enc)
            assert abs(w1-w2)<1e-10,"stringWidthU(%r,%r,%s,%r)-->%r != _py_stringWidth(...)-->%r" % (ts,fn,fontSize,enc,w1,w2)
        tfunc(testCp1252,t1fn,fontSize,enc)
        tfunc(ts,t1fn,fontSize,senc)
        tfunc(utext,t1fn,fontSize,senc)
        tfunc(ts,ttfn,fontSize,senc)
        tfunc(testCp1252,ttfn,fontSize,enc)
        tfunc(utext,ttfn,fontSize,senc)
        rcc = checkrc(defns,rcv)
        assert not rcc, "rc diffs (%s)" % rcc

    def test_instanceStringWidth(self):
        from reportlab.pdfbase.pdfmetrics import registerFont, getFont, _fonts, unicode2T1
        from reportlab.pdfbase.ttfonts import TTFont
        ttfn = 'Luxi-Serif'
        t1fn = 'Times-Roman'
        registerFont(TTFont(ttfn, "luxiserif.ttf"))
        ttf = getFont(ttfn)
        t1f = getFont(t1fn)
        testCp1252 = 'copyright %s trademark %s registered %s ReportLab! Ol%s!' % (chr(169), chr(153),chr(174), chr(0xe9))
        enc='cp1252'
        senc = 'utf8'
        ts = 'ABCDEF\xce\x91\xce\xb2G'
        utext = 'ABCDEF\xce\x91\xce\xb2G'.decode(senc)
        fontSize = 12
        defns="ttfn t1fn ttf t1f testCp1252 enc senc ts utext fontSize ttf.face ttf.face.charWidths ttf.face.defaultWidth t1f.widths t1f.encName t1f.substitutionFonts _fonts"
        rcv = getrc(defns)
        def tfunc(f,ts,fontSize,enc):
            w1 = f.stringWidth(ts,fontSize,enc)
            w2 = f._py_stringWidth(ts,fontSize,enc)
            assert abs(w1-w2)<1e-10,"f(%r).stringWidthU(%r,%s,%r)-->%r != f._py_stringWidth(...)-->%r" % (f,ts,fontSize,enc,w1,w2)
        tfunc(t1f,testCp1252,fontSize,enc)
        tfunc(t1f,ts,fontSize,senc)
        tfunc(t1f,utext,fontSize,senc)
        tfunc(ttf,ts,fontSize,senc)
        tfunc(ttf,testCp1252,fontSize,enc)
        tfunc(ttf,utext,fontSize,senc)
        rcc = checkrc(defns,rcv)
        assert not rcc, "rc diffs (%s)" % rcc

    def test_unicode2T1(self):
        from reportlab.pdfbase.pdfmetrics import _py_unicode2T1, getFont, _fonts
        from _rl_accel import unicode2T1
        t1fn = 'Times-Roman'
        t1f = getFont(t1fn)
        enc = 'cp1252'
        senc = 'utf8'
        testCp1252 = ('copyright %s trademark %s registered %s ReportLab! Ol%s!' % (chr(169), chr(153),chr(174), chr(0xe9))).decode(enc)
        utext = 'This is the end of the \xce\x91\xce\xb2 world. This is the end of the \xce\x91\xce\xb2 world jap=\xe3\x83\x9b\xe3\x83\x86. This is the end of the \xce\x91\xce\xb2 world. This is the end of the \xce\x91\xce\xb2 world jap=\xe3\x83\x9b\xe3\x83\x86'.decode('utf8')
        def tfunc(f,ts):
            w1 = unicode2T1(ts,[f]+f.substitutionFonts)
            w2 = _py_unicode2T1(ts,[f]+f.substitutionFonts)
            assert w1==w2,"%r != %r" % (w1,w2)
        defns="t1fn t1f testCp1252 enc senc utext t1f.widths t1f.encName t1f.substitutionFonts _fonts"
        rcv = getrc(defns)
        tfunc(t1f,testCp1252)
        tfunc(t1f,utext)
        rcc = checkrc(defns,rcv)
        assert not rcc, "rc diffs (%s)" % rcc

    def test_getFont(self):
        from reportlab.pdfbase.pdfmetrics import _py_getFont, getFont
        from _rl_accel import getFontU
        assert getFontU is getFont
        t1fn = 'Times-Roman'
        assert _py_getFont(t1fn) is getFontU(t1fn)

    def test_sameFrag(self):
        pass

def makeSuite():
    # only run the tests if _rl_accel is present
    try:
        import _rl_accel
        Klass = RlAccelTestCase
    except:
        class Klass(unittest.TestCase):
            pass
    return makeSuiteForClasses(Klass)

#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
