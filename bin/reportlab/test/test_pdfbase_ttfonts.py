
"""Test TrueType font subsetting & embedding code.

This test uses a sample font (luxiserif.ttf) taken from XFree86 which is called Luxi
Serif Regular and is covered under the license in ../fonts/luxiserif_licence.txt.
"""

import string
from cStringIO import StringIO

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation

from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfdoc import PDFDocument, PDFError
from reportlab.pdfbase.ttfonts import TTFont, TTFontFace, TTFontFile, TTFOpenFile, \
                                      TTFontParser, TTFontMaker, TTFError, \
                                      parse_utf8, makeToUnicodeCMap, \
                                      FF_SYMBOLIC, FF_NONSYMBOLIC, \
                                      calcChecksum, add32, _L2U32


def utf8(code):
    "Convert a given UCS character index into UTF-8"
    if code < 0 or code > 0x7FFFFFFF:
        raise ValueError, 'Invalid UCS character 0x%x' % code
    elif code < 0x00000080:
        return chr(code)
    elif code < 0x00000800:
        return '%c%c' % \
                 (0xC0 + (code >> 6),
                  0x80 + (code & 0x3F))
    elif code < 0x00010000:
        return '%c%c%c' % \
                 (0xE0 + (code >> 12),
                  0x80 + ((code >> 6) & 0x3F),
                  0x80 + (code & 0x3F))
    elif code < 0x00200000:
        return '%c%c%c%c' % \
                 (0xF0 + (code >> 18),
                  0x80 + ((code >> 12) & 0x3F),
                  0x80 + ((code >> 6) & 0x3F),
                  0x80 + (code & 0x3F))
    elif code < 0x04000000:
        return '%c%c%c%c%c' % \
                 (0xF8 + (code >> 24),
                  0x80 + ((code >> 18) & 0x3F),
                  0x80 + ((code >> 12) & 0x3F),
                  0x80 + ((code >> 6) & 0x3F),
                  0x80 + (code & 0x3F))
    else:
        return '%c%c%c%c%c%c' % \
                 (0xFC + (code >> 30),
                  0x80 + ((code >> 24) & 0x3F),
                  0x80 + ((code >> 18) & 0x3F),
                  0x80 + ((code >> 12) & 0x3F),
                  0x80 + ((code >> 6) & 0x3F),
                  0x80 + (code & 0x3F))

def _simple_subset_generation(fn,npages,alter=0):
    c = Canvas(outputfile(fn))
    c.setFont('Helvetica', 30)
    c.drawString(100,700, 'Unicode TrueType Font Test %d pages' % npages)
    # Draw a table of Unicode characters
    for p in xrange(npages):
        for fontName in ('TestFont','RinaFont'):
            c.setFont(fontName, 10)
            for i in xrange(32):
                for j in xrange(32):
                    ch = utf8(i * 32 + j+p*alter)
                    c.drawString(80 + j * 13 + int(j / 16) * 4, 600 - i * 13 - int(i / 8) * 8, ch)
        c.showPage()
    c.save()

class TTFontsTestCase(unittest.TestCase):
    "Make documents with TrueType fonts"

    def testTTF(self):
        "Test PDF generation with TrueType fonts"
        pdfmetrics.registerFont(TTFont("TestFont", "luxiserif.ttf"))
        pdfmetrics.registerFont(TTFont("RinaFont", "rina.ttf"))
        _simple_subset_generation('test_pdfbase_ttfonts1.pdf',1)
        _simple_subset_generation('test_pdfbase_ttfonts3.pdf',3)
        _simple_subset_generation('test_pdfbase_ttfonts35.pdf',3,5)

        # Do it twice with the same font object
        c = Canvas(outputfile('test_pdfbase_ttfontsadditional.pdf'))
        # Draw a table of Unicode characters
        c.setFont('TestFont', 10)
        c.drawString(100, 700, 'Hello, ' + utf8(0xffee))
        c.save()


class TTFontFileTestCase(unittest.TestCase):
    "Tests TTFontFile, TTFontParser and TTFontMaker classes"

    def testFontFileFailures(self):
        "Tests TTFontFile constructor error checks"
        self.assertRaises(TTFError, TTFontFile, "nonexistent file")
        self.assertRaises(TTFError, TTFontFile, StringIO(""))
        self.assertRaises(TTFError, TTFontFile, StringIO("invalid signature"))
        self.assertRaises(TTFError, TTFontFile, StringIO("OTTO - OpenType not supported yet"))
        self.assertRaises(TTFError, TTFontFile, StringIO("\0\1\0\0"))

    def testFontFileReads(self):
        "Tests TTFontParset.read_xxx"

        class FakeTTFontFile(TTFontParser):
            def __init__(self, data):
                self._ttf_data = data
                self._pos = 0

        ttf = FakeTTFontFile("\x81\x02\x03\x04" "\x85\x06" "ABCD" "\x7F\xFF" "\x80\x00" "\xFF\xFF")
        self.assertEquals(ttf.read_ulong(), _L2U32(0x81020304L)) # big-endian
        self.assertEquals(ttf._pos, 4)
        self.assertEquals(ttf.read_ushort(), 0x8506)
        self.assertEquals(ttf._pos, 6)
        self.assertEquals(ttf.read_tag(), 'ABCD')
        self.assertEquals(ttf._pos, 10)
        self.assertEquals(ttf.read_short(), 0x7FFF)
        self.assertEquals(ttf.read_short(), -0x8000)
        self.assertEquals(ttf.read_short(), -1)

    def testFontFile(self):
        "Tests TTFontFile and TTF parsing code"
        ttf = TTFontFile("luxiserif.ttf")
        self.assertEquals(ttf.name, "LuxiSerif")
        self.assertEquals(ttf.flags, FF_SYMBOLIC)
        self.assertEquals(ttf.italicAngle, 0.0)
        self.assertEquals(ttf.ascent, 783)      # FIXME: or 992?
        self.assertEquals(ttf.descent, -206)    # FIXME: or -210?
        self.assertEquals(ttf.capHeight, 0)
        self.assertEquals(ttf.bbox, [-204, -211, 983, 992])
        self.assertEquals(ttf.stemV, 87)
        self.assertEquals(ttf.defaultWidth, 250)

    def testAdd32(self):
        "Test add32"
        self.assertEquals(add32(10, -6), 4)
        self.assertEquals(add32(6, -10), -4)
        self.assertEquals(add32(_L2U32(0x80000000L), -1), 0x7FFFFFFF)
        self.assertEquals(add32(0x7FFFFFFF, 1), _L2U32(0x80000000L))

    def testChecksum(self):
        "Test calcChecksum function"
        self.assertEquals(calcChecksum(""), 0)
        self.assertEquals(calcChecksum("\1"), 0x01000000)
        self.assertEquals(calcChecksum("\x01\x02\x03\x04\x10\x20\x30\x40"), 0x11223344)
        self.assertEquals(calcChecksum("\x81"), _L2U32(0x81000000L))
        self.assertEquals(calcChecksum("\x81\x02"), _L2U32(0x81020000L))
        self.assertEquals(calcChecksum("\x81\x02\x03"), _L2U32(0x81020300L))
        self.assertEquals(calcChecksum("\x81\x02\x03\x04"), _L2U32(0x81020304L))
        self.assertEquals(calcChecksum("\x81\x02\x03\x04\x05"), _L2U32(0x86020304L))
        self.assertEquals(calcChecksum("\x41\x02\x03\x04\xD0\x20\x30\x40"), 0x11223344)
        self.assertEquals(calcChecksum("\xD1\x02\x03\x04\x40\x20\x30\x40"), 0x11223344)
        self.assertEquals(calcChecksum("\x81\x02\x03\x04\x90\x20\x30\x40"), 0x11223344)
        self.assertEquals(calcChecksum("\x7F\xFF\xFF\xFF\x00\x00\x00\x01"), _L2U32(0x80000000L))

    def testFontFileChecksum(self):
        "Tests TTFontFile and TTF parsing code"
        file = TTFOpenFile("luxiserif.ttf")[1].read()
        TTFontFile(StringIO(file), validate=1) # should not fail
        file1 = file[:12345] + "\xFF" + file[12346:] # change one byte
        self.assertRaises(TTFError, TTFontFile, StringIO(file1), validate=1)
        file1 = file[:8] + "\xFF" + file[9:] # change one byte
        self.assertRaises(TTFError, TTFontFile, StringIO(file1), validate=1)

    def testSubsetting(self):
        "Tests TTFontFile and TTF parsing code"
        ttf = TTFontFile("luxiserif.ttf")
        subset = ttf.makeSubset([0x41, 0x42])
        subset = TTFontFile(StringIO(subset), 0)
        for tag in ('cmap', 'head', 'hhea', 'hmtx', 'maxp', 'name', 'OS/2',
                    'post', 'cvt ', 'fpgm', 'glyf', 'loca', 'prep'):
            self.assert_(subset.get_table(tag))

        subset.seek_table('loca')
        for n in range(4):
            pos = subset.read_ushort()    # this is actually offset / 2
            self.failIf(pos % 2 != 0, "glyph %d at +%d should be long aligned" % (n, pos * 2))

        self.assertEquals(subset.name, "LuxiSerif")
        self.assertEquals(subset.flags, FF_SYMBOLIC)
        self.assertEquals(subset.italicAngle, 0.0)
        self.assertEquals(subset.ascent, 783)      # FIXME: or 992?
        self.assertEquals(subset.descent, -206)    # FIXME: or -210?
        self.assertEquals(subset.capHeight, 0)
        self.assertEquals(subset.bbox, [-204, -211, 983, 992])
        self.assertEquals(subset.stemV, 87)

    def testFontMaker(self):
        "Tests TTFontMaker class"
        ttf = TTFontMaker()
        ttf.add("ABCD", "xyzzy")
        ttf.add("QUUX", "123")
        ttf.add("head", "12345678xxxx")
        stm = ttf.makeStream()
        ttf = TTFontParser(StringIO(stm), 0)
        self.assertEquals(ttf.get_table("ABCD"), "xyzzy")
        self.assertEquals(ttf.get_table("QUUX"), "123")


class TTFontFaceTestCase(unittest.TestCase):
    "Tests TTFontFace class"

    def testAddSubsetObjects(self):
        "Tests TTFontFace.addSubsetObjects"
        face = TTFontFace("luxiserif.ttf")
        doc = PDFDocument()
        fontDescriptor = face.addSubsetObjects(doc, "TestFont", [ 0x78, 0x2017 ])
        fontDescriptor = doc.idToObject[fontDescriptor.name].dict
        self.assertEquals(fontDescriptor['Type'], '/FontDescriptor')
        self.assertEquals(fontDescriptor['Ascent'], face.ascent)
        self.assertEquals(fontDescriptor['CapHeight'], face.capHeight)
        self.assertEquals(fontDescriptor['Descent'], face.descent)
        self.assertEquals(fontDescriptor['Flags'], (face.flags & ~FF_NONSYMBOLIC) | FF_SYMBOLIC)
        self.assertEquals(fontDescriptor['FontName'], "/TestFont")
        self.assertEquals(fontDescriptor['FontBBox'].sequence, face.bbox)
        self.assertEquals(fontDescriptor['ItalicAngle'], face.italicAngle)
        self.assertEquals(fontDescriptor['StemV'], face.stemV)
        fontFile = fontDescriptor['FontFile2']
        fontFile = doc.idToObject[fontFile.name]
        self.assert_(fontFile.content != "")


class TTFontTestCase(unittest.TestCase):
    "Tests TTFont class"

    def testParseUTF8(self):
        "Tests parse_utf8"
        self.assertEquals(parse_utf8(""), [])
        for i in range(0, 0x80):
            self.assertEquals(parse_utf8(chr(i)), [i])
        for i in range(0x80, 0xA0):
            self.assertRaises(ValueError, parse_utf8, chr(i))
        self.assertEquals(parse_utf8("abc"), [0x61, 0x62, 0x63])
        self.assertEquals(parse_utf8("\xC2\xA9x"), [0xA9, 0x78])
        self.assertEquals(parse_utf8("\xE2\x89\xA0x"), [0x2260, 0x78])
        self.assertRaises(ValueError, parse_utf8, "\xE2\x89x")
        # for i in range(0, 0xFFFF): - overkill
        for i in range(0x80, 0x200) + range(0x300, 0x400) + [0xFFFE, 0xFFFF]:
            self.assertEquals(parse_utf8(utf8(i)), [i])

    def testStringWidth(self):
        "Test TTFont.stringWidth"
        font = TTFont("TestFont", "luxiserif.ttf")
        self.assert_(font.stringWidth("test", 10) > 0)
        width = font.stringWidth(utf8(0x2260) * 2, 1000)
        expected = font.face.getCharWidth(0x2260) * 2
        self.assert_(abs(width - expected) < 0.01, "%g != %g" % (width, expected))

    def testSplitString(self):
        "Tests TTFont.splitString"
        doc = PDFDocument()
        font = TTFont("TestFont", "luxiserif.ttf")
        text = string.join(map(utf8, xrange(0, 511)), "")
        allchars = string.join(map(chr, xrange(0, 256)), "")
        nospace = allchars[:32] + allchars[33:]
        chunks = [(0, allchars), (1, nospace)]
        self.assertEquals(font.splitString(text, doc), chunks)
        # Do it twice
        self.assertEquals(font.splitString(text, doc), chunks)

        text = string.join(map(utf8, range(510, -1, -1)), "")
        allchars = string.join(map(chr, range(255, -1, -1)), "")
        nospace = allchars[:223] + allchars[224:]
        chunks = [(1, nospace), (0, allchars)]
        self.assertEquals(font.splitString(text, doc), chunks)

    def testSplitStringSpaces(self):
        # In order for justification (word spacing) to work, the space
        # glyph must have a code 32, and no other character should have
        # that code in any subset, or word spacing will be applied to it.

        doc = PDFDocument()
        font = TTFont("TestFont", "luxiserif.ttf")
        text = string.join(map(utf8, range(512, -1, -1)), "")
        chunks = font.splitString(text, doc)
        state = font.state[doc]
        self.assertEquals(state.assignments[32], 32)
        self.assertEquals(state.subsets[0][32], 32)
        self.assertEquals(state.subsets[1][32], 32)

    def testSubsetInternalName(self):
        "Tests TTFont.getSubsetInternalName"
        doc = PDFDocument()
        font = TTFont("TestFont", "luxiserif.ttf")
        # Actually generate some subsets
        text = string.join(map(utf8, range(0, 513)), "")
        font.splitString(text, doc)
        self.assertRaises(IndexError, font.getSubsetInternalName, -1, doc)
        self.assertRaises(IndexError, font.getSubsetInternalName, 3, doc)
        self.assertEquals(font.getSubsetInternalName(0, doc), "/F1+0")
        self.assertEquals(font.getSubsetInternalName(1, doc), "/F1+1")
        self.assertEquals(font.getSubsetInternalName(2, doc), "/F1+2")
        self.assertEquals(doc.delayedFonts, [font])

    def testAddObjectsEmpty(self):
        "TTFont.addObjects should not fail when no characters were used"
        font = TTFont("TestFont", "luxiserif.ttf")
        doc = PDFDocument()
        font.addObjects(doc)

    def no_longer_testAddObjectsResets(self):
        "Test that TTFont.addObjects resets the font"
        # Actually generate some subsets
        doc = PDFDocument()
        font = TTFont("TestFont", "luxiserif.ttf")
        font.splitString('a', doc)            # create some subset
        doc = PDFDocument()
        font.addObjects(doc)
        self.assertEquals(font.frozen, 0)
        self.assertEquals(font.nextCode, 0)
        self.assertEquals(font.subsets, [])
        self.assertEquals(font.assignments, {})
        font.splitString('ba', doc)           # should work

    def testParallelConstruction(self):
        "Test that TTFont can be used for different documents at the same time"
        doc1 = PDFDocument()
        doc2 = PDFDocument()
        font = TTFont("TestFont", "luxiserif.ttf")
        self.assertEquals(font.splitString(u'hello ', doc1), [(0, 'hello ')])
        self.assertEquals(font.splitString(u'hello ', doc2), [(0, 'hello ')])
        self.assertEquals(font.splitString(u'\u0410\u0411'.encode('UTF-8'), doc1), [(0, '\x80\x81')])
        self.assertEquals(font.splitString(u'\u0412'.encode('UTF-8'), doc2), [(0, '\x80')])
        font.addObjects(doc1)
        self.assertEquals(font.splitString(u'\u0413'.encode('UTF-8'), doc2), [(0, '\x81')])
        font.addObjects(doc2)

    def testAddObjects(self):
        "Test TTFont.addObjects"
        # Actually generate some subsets
        doc = PDFDocument()
        font = TTFont("TestFont", "luxiserif.ttf")
        font.splitString('a', doc)            # create some subset
        internalName = font.getSubsetInternalName(0, doc)[1:]
        font.addObjects(doc)
        pdfFont = doc.idToObject[internalName]
        self.assertEquals(doc.idToObject['BasicFonts'].dict[internalName], pdfFont)
        self.assertEquals(pdfFont.Name, internalName)
        self.assertEquals(pdfFont.BaseFont, "AAAAAA+LuxiSerif")
        self.assertEquals(pdfFont.FirstChar, 0)
        self.assertEquals(pdfFont.LastChar, 127)
        self.assertEquals(len(pdfFont.Widths.sequence), 128)
        toUnicode = doc.idToObject[pdfFont.ToUnicode.name]
        self.assert_(toUnicode.content != "")
        fontDescriptor = doc.idToObject[pdfFont.FontDescriptor.name]
        self.assertEquals(fontDescriptor.dict['Type'], '/FontDescriptor')

    def testMakeToUnicodeCMap(self):
        "Test makeToUnicodeCMap"
        self.assertEquals(makeToUnicodeCMap("TestFont", [ 0x1234, 0x4321, 0x4242 ]),
"""/CIDInit /ProcSet findresource begin
12 dict begin
begincmap
/CIDSystemInfo
<< /Registry (TestFont)
/Ordering (TestFont)
/Supplement 0
>> def
/CMapName /TestFont def
/CMapType 2 def
1 begincodespacerange
<00> <02>
endcodespacerange
3 beginbfchar
<00> <1234>
<01> <4321>
<02> <4242>
endbfchar
endcmap
CMapName currentdict /CMap defineresource pop
end
end""")


def makeSuite():
    suite = makeSuiteForClasses(
        TTFontsTestCase,
        TTFontFileTestCase,
        TTFontFaceTestCase,
        TTFontTestCase)
    return suite


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
