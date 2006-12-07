#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/pdfbase/pdfmetrics.py
#$Header $
__version__=''' $Id$ '''
__doc__="""
This provides a database of font metric information and
efines Font, Encoding and TypeFace classes aimed at end users.

There are counterparts to some of these in pdfbase/pdfdoc.py, but
the latter focus on constructing the right PDF objects.  These
classes are declarative and focus on letting the user construct
and query font objects.

The module maintains a registry of font objects at run time.

It is independent of the canvas or any particular context.  It keeps
a registry of Font, TypeFace and Encoding objects.  Ideally these
would be pre-loaded, but due to a nasty circularity problem we
trap attempts to access them and do it on first access.
"""
import string, os
from types import StringType, ListType, TupleType
from reportlab.pdfbase import _fontdata
from reportlab.lib.logger import warnOnce
from reportlab.lib.utils import rl_isfile, open_and_read, open_and_readlines 
from reportlab.rl_config import defaultEncoding

standardFonts = _fontdata.standardFonts
standardEncodings = _fontdata.standardEncodings

_dummyEncoding=' _not an encoding_ '
# conditional import - try both import techniques, and set a flag
try:
    import _rl_accel
    try:
        _stringWidth = _rl_accel.stringWidth
        _rl_accel.defaultEncoding(_dummyEncoding)
    except:
        _stringWidth = None
except ImportError:
    _stringWidth = None

_typefaces = {}
_encodings = {}
_fonts = {}

class FontError(Exception):
    pass
class FontNotFoundError(Exception):
    pass

def parseAFMFile(afmFileName):
    """Quick and dirty - gives back a top-level dictionary
    with top-level items, and a 'widths' key containing
    a dictionary of glyph names and widths.  Just enough
    needed for embedding.  A better parser would accept
    options for what data you wwanted, and preserve the
    order."""

    lines = open_and_readlines(afmFileName, 'r')
    if len(lines)<=1:
        #likely to be a MAC file
        lines = string.split(lines,'\r')
        if len(lines)<=1:
            raise ValueError, 'AFM file %s hasn\'t enough data' % afmFileName
    topLevel = {}
    glyphLevel = []

    lines = map(string.strip, lines)
    #pass 1 - get the widths
    inMetrics = 0  # os 'TOP', or 'CHARMETRICS'
    for line in lines:
        if line[0:16] == 'StartCharMetrics':
            inMetrics = 1
        elif line[0:14] == 'EndCharMetrics':
            inMetrics = 0
        elif inMetrics:
            chunks = string.split(line, ';')
            chunks = map(string.strip, chunks)
            cidChunk, widthChunk, nameChunk = chunks[0:3]

            # character ID
            l, r = string.split(cidChunk)
            assert l == 'C', 'bad line in font file %s' % line
            cid = string.atoi(r)

            # width
            l, r = string.split(widthChunk)
            assert l == 'WX', 'bad line in font file %s' % line
            width = string.atoi(r)

            # name
            l, r = string.split(nameChunk)
            assert l == 'N', 'bad line in font file %s' % line
            name = r

            glyphLevel.append((cid, width, name))

    # pass 2 font info
    inHeader = 0
    for line in lines:
        if line[0:16] == 'StartFontMetrics':
            inHeader = 1
        if line[0:16] == 'StartCharMetrics':
            inHeader = 0
        elif inHeader:
            if line[0:7] == 'Comment': pass
            try:
                left, right = string.split(line,' ',1)
            except:
                raise ValueError, "Header information error in afm %s: line='%s'" % (afmFileName, line)
            try:
                right = string.atoi(right)
            except:
                pass
            topLevel[left] = right


    return (topLevel, glyphLevel)

class TypeFace:
    def __init__(self, name):
        self.name = name
        self.glyphNames = []
        self.glyphWidths = {}
        self.ascent = 0
        self.descent = 0


        # all typefaces of whatever class should have these 3 attributes.
        # these are the basis for family detection.
        self.familyName = None  # should set on load/construction if possible
        self.bold = 0    # bold faces should set this
        self.italic = 0  #italic faces should set this

        
        if name == 'ZapfDingbats':
            self.requiredEncoding = 'ZapfDingbatsEncoding'
        elif name == 'Symbol':
            self.requiredEncoding = 'SymbolEncoding'
        else:
            self.requiredEncoding = None
        if name in standardFonts:
            self.builtIn = 1
            self._loadBuiltInData(name)
        else:
            self.builtIn = 0

    def _loadBuiltInData(self, name):
        """Called for the built in 14 fonts.  Gets their glyph data.
        We presume they never change so this can be a shared reference."""
        name = str(name)    #needed for pycanvas&jython/2.1 compatibility
        self.glyphWidths = _fontdata.widthsByFontGlyph[name]
        self.glyphNames = self.glyphWidths.keys()
        self.ascent,self.descent = _fontdata.ascent_descent[name]

    def getFontFiles(self):
        "Info function, return list of the font files this depends on."
        return []

    def findT1File(self, ext='.pfb'):
        possible_exts = (string.lower(ext), string.upper(ext))
        if hasattr(self,'pfbFileName'):
            r_basename = os.path.splitext(self.pfbFileName)[0]
            for e in possible_exts:
                if rl_isfile(r_basename + e):
                    return r_basename + e
        try:
            r = _fontdata.findT1File(self.name)
        except:
            afm = bruteForceSearchForAFM(self.name)
            if afm:
                if string.lower(ext) == '.pfb':
                    for e in possible_exts:
                        pfb = os.path.splitext(afm)[0] + e
                        if rl_isfile(pfb):
                            r = pfb
                        else:
                            r = None
                elif string.lower(ext) == '.afm':
                    r = afm
            else:
                r = None
        if r is None:
            warnOnce("Can't find %s for face '%s'" % (ext, self.name))
        return r

def bruteForceSearchForAFM(faceName):
    """Looks in all AFM files on path for face with given name.

    Returns AFM file name or None.  Ouch!"""
    import glob
    from reportlab.rl_config import T1SearchPath

    for dirname in T1SearchPath:
        if not os.path.isdir(dirname):
            continue
        possibles = glob.glob(dirname + os.sep + '*.[aA][fF][mM]')
        for possible in possibles:
            (topDict, glyphDict) = parseAFMFile(possible)
            if topDict['FontName'] == faceName:
                return possible
    return None



#for faceName in standardFonts:
#    registerTypeFace(TypeFace(faceName))


class Encoding:
    """Object to help you create and refer to encodings."""
    def __init__(self, name, base=None):
        self.name = name
        self.frozen = 0
        if name in standardEncodings:
            assert base is None, "Can't have a base encoding for a standard encoding"
            self.baseEncodingName = name
            self.vector = _fontdata.encodings[name]
        elif base == None:
            # assume based on the usual one
            self.baseEncodingName = defaultEncoding
            self.vector = _fontdata.encodings[defaultEncoding]
        elif type(base) is StringType:
            baseEnc = getEncoding(base)
            self.baseEncodingName = baseEnc.name
            self.vector = baseEnc.vector[:]
        elif type(base) in (ListType, TupleType):
            self.baseEncodingName = defaultEncoding
            self.vector = base[:]
        elif isinstance(base, Encoding):
            # accept a vector
            self.baseEncodingName = base.name
            self.vector = base.vector[:]

    def __getitem__(self, index):
        "Return glyph name for that code point, or None"
        # THIS SHOULD BE INLINED FOR SPEED
        return self.vector[index]

    def __setitem__(self, index, value):
        # should fail if they are frozen
        assert self.frozen == 0, 'Cannot modify a frozen encoding'
        if self.vector[index]!=value:
            L = list(self.vector)
            L[index] = value
            self.vector = tuple(L)

    def freeze(self):
        self.vector = tuple(self.vector)
        self.frozen = 1

    def isEqual(self, other):
        return ((self.name == other.name) and (self.vector == other.vector))

    def modifyRange(self, base, newNames):
        """Set a group of character names starting at the code point 'base'."""
        assert self.frozen == 0, 'Cannot modify a frozen encoding'
        idx = base
        for name in newNames:
            self.vector[idx] = name
            idx = idx + 1

    def getDifferences(self, otherEnc):
        """Return a compact list of the code points differing between two encodings

        This is in the Adobe format: list of
           [[b1, name1, name2, name3],
           [b2, name4]]
        where b1...bn is the starting code point, and the glyph names following
        are assigned consecutive code points."""

        ranges = []
        curRange = None
        for i in xrange(len(self.vector)):
            glyph = self.vector[i]
            if glyph==otherEnc.vector[i]:
                if curRange:
                    ranges.append(curRange)
                    curRange = []
            else:
                if curRange:
                    curRange.append(glyph)
                elif glyph:
                    curRange = [i, glyph]
        if curRange:
            ranges.append(curRange)
        return ranges

    def makePDFObject(self):
        "Returns a PDF Object representing self"
        # avoid circular imports - this cannot go at module level
        from reportlab.pdfbase import pdfdoc

        D = {}
        baseEnc = getEncoding(self.baseEncodingName)
        differences = self.getDifferences(baseEnc) #[None] * 256)

        # if no differences, we just need the base name
        if differences == []:
            return pdfdoc.PDFName(self.baseEncodingName)
        else:
            #make up a dictionary describing the new encoding
            diffArray = []
            for range in differences:
                diffArray.append(range[0])        # numbers go 'as is'
                for glyphName in range[1:]:
                    if glyphName is not None:
                        # there is no way to 'unset' a character in the base font.
                        diffArray.append('/' + glyphName)

            #print 'diffArray = %s' % diffArray
            D["Differences"] = pdfdoc.PDFArray(diffArray)
            D["BaseEncoding"] = pdfdoc.PDFName(self.baseEncodingName)
            D["Type"] = pdfdoc.PDFName("Encoding")
            PD = pdfdoc.PDFDictionary(D)
            return PD

#for encName in standardEncodings:
#    registerEncoding(Encoding(encName))

class Font:
    """Represents a font (i.e combination of face and encoding).

    Defines suitable machinery for single byte fonts.  This is
    a concrete class which can handle the basic built-in fonts;
    not clear yet if embedded ones need a new font class or
    just a new typeface class (which would do the job through
    composition)"""
    def __init__(self, name, faceName, encName):
        self.fontName = name
        self.face = getTypeFace(faceName)
        self.encoding= getEncoding(encName)
        self._calcWidths()

        # multi byte fonts do their own stringwidth calculations.
        # signal this here.
        self._multiByte = 0

    def _calcWidths(self):
        """Vector of widths for stringWidth function"""
        #synthesize on first request
        w = [0] * 256
        gw = self.face.glyphWidths
        vec = self.encoding.vector
        for i in range(256):
            glyphName = vec[i]
            if glyphName is not None:
                try:
                    width = gw[glyphName]
                    w[i] = width
                except KeyError:
                    import reportlab.rl_config
                    if reportlab.rl_config.warnOnMissingFontGlyphs:
                        print 'typeface "%s" does not have a glyph "%s", bad font!' % (self.face.name, glyphName)
                    else:
                        pass
        self.widths = w

    if not _stringWidth:
        def stringWidth(self, text, size):
            """This is the "purist" approach to width.  The practical one
            is to use the stringWidth one which may be optimized
            in C."""
            w = 0
            widths = self.widths
            for ch in text:
                w = w + widths[ord(ch)]
            return w * 0.001 * size

    def _formatWidths(self):
        "returns a pretty block in PDF Array format to aid inspection"
        text = '['
        for i in range(256):
            text = text + ' ' + str(self.widths[i])
            if i == 255:
                text = text + ' ]'
            if i % 16 == 15:
                text = text + '\n'
        return text

    def addObjects(self, doc):
        """Makes and returns one or more PDF objects to be added
        to the document.  The caller supplies the internal name
        to be used (typically F1, F2... in sequence) """
        # avoid circular imports - this cannot go at module level
        from reportlab.pdfbase import pdfdoc

        # construct a Type 1 Font internal object
        internalName = 'F' + repr(len(doc.fontMapping)+1)
        pdfFont = pdfdoc.PDFType1Font()
        pdfFont.Name = internalName
        pdfFont.BaseFont = self.face.name
        pdfFont.__Comment__ = 'Font %s' % self.fontName
        pdfFont.Encoding = self.encoding.makePDFObject()

        # is it a built-in one?  if not, need more stuff.
        if not self.face.name in standardFonts:
            pdfFont.FirstChar = 0
            pdfFont.LastChar = 255
            pdfFont.Widths = pdfdoc.PDFArray(self.widths)
            pdfFont.FontDescriptor = self.face.addObjects(doc)
        # now link it in
        ref = doc.Reference(pdfFont, internalName)

        # also refer to it in the BasicFonts dictionary
        fontDict = doc.idToObject['BasicFonts'].dict
        fontDict[internalName] = pdfFont

        # and in the font mappings
        doc.fontMapping[self.fontName] = '/' + internalName

PFB_MARKER=chr(0x80)
PFB_ASCII=chr(1)
PFB_BINARY=chr(2)
PFB_EOF=chr(3)
def _pfbSegLen(p,d):
    '''compute a pfb style length from the first 4 bytes of string d'''
    return ((((ord(d[p+3])<<8)|ord(d[p+2])<<8)|ord(d[p+1]))<<8)|ord(d[p])

def _pfbCheck(p,d,m,fn):
    if d[p]!=PFB_MARKER or d[p+1]!=m:
        raise ValueError, 'Bad pfb file\'%s\' expected chr(%d)chr(%d) at char %d, got chr(%d)chr(%d)' % (fn,ord(PFB_MARKER),ord(m),p,ord(d[p]),ord(d[p+1]))
    if m==PFB_EOF: return
    p = p + 2
    l = _pfbSegLen(p,d)
    p = p + 4
    if p+l>len(d):
        raise ValueError, 'Bad pfb file\'%s\' needed %d+%d bytes have only %d!' % (fn,p,l,len(d))
    return p, p+l


class EmbeddedType1Face(TypeFace):
    """A Type 1 font other than one of the basic 14.

    Its glyph data will be embedded in the PDF file."""
    def __init__(self, afmFileName, pfbFileName):
        # ignore afm file for now
        TypeFace.__init__(self, None)
        #None is a hack, name will be supplied by AFM parse lower done
        #in this __init__ method.
        self.afmFileName = os.path.abspath(afmFileName)
        self.pfbFileName = os.path.abspath(pfbFileName)
        self.requiredEncoding = None
        self._loadGlyphs(pfbFileName)
        self._loadMetrics(afmFileName)

    def getFontFiles(self):
        return [self.afmFileName, self.pfbFileName]
    
    def _loadGlyphs(self, pfbFileName):
        """Loads in binary glyph data, and finds the four length
        measurements needed for the font descriptor"""
        assert rl_isfile(pfbFileName), 'file %s not found' % pfbFileName
        d = open_and_read(pfbFileName, 'b')
        s1, l1 = _pfbCheck(0,d,PFB_ASCII,pfbFileName)
        s2, l2 = _pfbCheck(l1,d,PFB_BINARY,pfbFileName)
        s3, l3 = _pfbCheck(l2,d,PFB_ASCII,pfbFileName)
        _pfbCheck(l3,d,PFB_EOF,pfbFileName)
        self._binaryData = d[s1:l1]+d[s2:l2]+d[s3:l3]

        self._length = len(self._binaryData)
        self._length1 = l1-s1
        self._length2 = l2-s2
        self._length3 = l3-s3


    def _loadMetrics(self, afmFileName):
        """Loads in and parses font metrics"""
        #assert os.path.isfile(afmFileName), "AFM file %s not found" % afmFileName
        (topLevel, glyphData) = parseAFMFile(afmFileName)

        self.name = topLevel['FontName']
        self.familyName = topLevel['FamilyName']
        self.ascent = topLevel.get('Ascender', 1000)
        self.descent = topLevel.get('Descender', 0)
        self.capHeight = topLevel.get('CapHeight', 1000)
        self.italicAngle = topLevel.get('ItalicAngle', 0)
        self.stemV = topLevel.get('stemV', 0)
        self.xHeight = topLevel.get('XHeight', 1000)

        strBbox = topLevel.get('FontBBox', [0,0,1000,1000])
        tokens = string.split(strBbox)
        self.bbox = []
        for tok in tokens:
            self.bbox.append(string.atoi(tok))

        glyphWidths = {}
        for (cid, width, name) in glyphData:
            glyphWidths[name] = width
        self.glyphWidths = glyphWidths
        self.glyphNames = glyphWidths.keys()
        self.glyphNames.sort()

        # for font-specific encodings like Symbol, Dingbats, Carta we
        # need to make a new encoding as well....
        if topLevel.get('EncodingScheme', None) == 'FontSpecific':
            names = [None] * 256
            for (code, width, name) in glyphData:
                if code >=0 and code <=255:
                    names[code] = name
            encName = self.name + 'Encoding'
            self.requiredEncoding = encName
            enc = Encoding(encName, names)
            registerEncoding(enc)

    def addObjects(self, doc):
        """Add whatever needed to PDF file, and return a FontDescriptor reference"""
        from reportlab.pdfbase import pdfdoc

        fontFile = pdfdoc.PDFStream()
        fontFile.content = self._binaryData
        #fontFile.dictionary['Length'] = self._length
        fontFile.dictionary['Length1'] = self._length1
        fontFile.dictionary['Length2'] = self._length2
        fontFile.dictionary['Length3'] = self._length3
        #fontFile.filters = [pdfdoc.PDFZCompress]

        fontFileRef = doc.Reference(fontFile, 'fontFile:' + self.pfbFileName)

        fontDescriptor = pdfdoc.PDFDictionary({
            'Type': '/FontDescriptor',
            'Ascent':self.ascent,
            'CapHeight':self.capHeight,
            'Descent':self.descent,
            'Flags': 34,
            'FontBBox':pdfdoc.PDFArray(self.bbox),
            'FontName':pdfdoc.PDFName(self.name),
            'ItalicAngle':self.italicAngle,
            'StemV':self.stemV,
            'XHeight':self.xHeight,
            'FontFile': fontFileRef,
            })
        fontDescriptorRef = doc.Reference(fontDescriptor, 'fontDescriptor:' + self.name)
        return fontDescriptorRef

def registerTypeFace(face):
    assert isinstance(face, TypeFace), 'Not a TypeFace: %s' % face
    _typefaces[face.name] = face
    # HACK - bold/italic do not apply for type 1, so egister
    # all combinations of mappings.
    from reportlab.lib import fonts
    ttname = string.lower(face.name)
    if not face.name in standardFonts:
        fonts.addMapping(ttname, 0, 0, face.name)
        fonts.addMapping(ttname, 1, 0, face.name)
        fonts.addMapping(ttname, 0, 1, face.name)
        fonts.addMapping(ttname, 1, 1, face.name)

def registerEncoding(enc):
    assert isinstance(enc, Encoding), 'Not an Encoding: %s' % enc
    if _encodings.has_key(enc.name):
        # already got one, complain if they are not the same
        if enc.isEqual(_encodings[enc.name]):
            enc.freeze()
        else:
            raise FontError('Encoding "%s" already registered with a different name vector!' % enc.Name)
    else:
        _encodings[enc.name] = enc
        enc.freeze()
    # have not yet dealt with immutability!

def registerFont(font):
    "Registers a font, including setting up info for accelerated stringWidth"
    #assert isinstance(font, Font), 'Not a Font: %s' % font
    fontName = font.fontName
    _fonts[fontName] = font
    if font._multiByte:
        # CID fonts don't need to have typeface registered.
        #need to set mappings so it can go in a paragraph even if within
        # bold tags
        from reportlab.lib import fonts
        ttname = string.lower(font.fontName)
        fonts.addMapping(ttname, 0, 0, font.fontName)
        fonts.addMapping(ttname, 1, 0, font.fontName)
        fonts.addMapping(ttname, 0, 1, font.fontName)
        fonts.addMapping(ttname, 1, 1, font.fontName)
        #cannot accelerate these yet...
    else:
        if _stringWidth:
            _rl_accel.setFontInfo(string.lower(fontName),
                                  _dummyEncoding,
                                  font.face.ascent,
                                  font.face.descent,
                                  font.widths)


def getTypeFace(faceName):
    """Lazily construct known typefaces if not found"""
    try:
        return _typefaces[faceName]
    except KeyError:
        # not found, construct it if known
        if faceName in standardFonts:
            face = TypeFace(faceName)
            (face.familyName, face.bold, face.italic) = _fontdata.standardFontAttributes[faceName]
            registerTypeFace(face)
##            print 'auto-constructing type face %s with family=%s, bold=%d, italic=%d' % (
##                face.name, face.familyName, face.bold, face.italic)
            return face
        else:
            #try a brute force search
            afm = bruteForceSearchForAFM(faceName)
            if afm:
                for e in ('.pfb', '.PFB'):
                    pfb = os.path.splitext(afm)[0] + e
                    if rl_isfile(pfb): break
                assert rl_isfile(pfb), 'file %s not found!' % pfb
                face = EmbeddedType1Face(afm, pfb)
                registerTypeFace(face)
                return face
            else:
                raise

def getEncoding(encName):
    """Lazily construct known encodings if not found"""
    try:
        return _encodings[encName]
    except KeyError:
        if encName in standardEncodings:
            enc = Encoding(encName)
            registerEncoding(enc)
            #print 'auto-constructing encoding %s' % encName
            return enc
        else:
            raise

def getFont(fontName):
    """Lazily constructs known fonts if not found.

    Names of form 'face-encoding' will be built if
    face and encoding are known.  Also if the name is
    just one of the standard 14, it will make up a font
    in the default encoding."""
    try:
        return _fonts[fontName]
    except KeyError:
        #it might have a font-specific encoding e.g. Symbol
        # or Dingbats.  If not, take the default.
        face = getTypeFace(fontName)
        if face.requiredEncoding:
            font = Font(fontName, fontName, face.requiredEncoding)
        else:
            font = Font(fontName, fontName, defaultEncoding)
        registerFont(font)
        return font

def getRegisteredFontNames():
    "Returns what's in there"
    reg = _fonts.keys()
    reg.sort()
    return reg

def _slowStringWidth(text, fontName, fontSize):
    """Define this anyway so it can be tested, but whether it is used or not depends on _rl_accel"""
    font = getFont(fontName)
    return font.stringWidth(text, fontSize)
    #this is faster, but will need more special-casing for multi-byte fonts.
    #wid = getFont(fontName).widths
    #w = 0
    #for ch in text:
    #    w = w + wid[ord(ch)]
    #return 0.001 * w * fontSize


if _stringWidth:
    import new
    Font.stringWidth = new.instancemethod(_rl_accel._instanceStringWidth,None,Font)
    stringWidth = _stringWidth

    #if accelerator present, make sure we at least
    #register Courier font, since it will fall back to Courier
    #as its default font.
    f = getFont('Courier')


    def _SWRecover(text, fontName, fontSize, encoding):
        '''This is called when _rl_accel's database doesn't know about a font.
        Currently encoding is always a dummy.
        '''
        try:
            font = getFont(fontName)
            if font._multiByte:
                return font.stringWidth(text, fontSize)
            else:
                registerFont(font)
                return _stringWidth(text,fontName,fontSize,encoding)
        except:
            warnOnce('Font %s:%s not found - using Courier:%s for widths'%(fontName,encoding,encoding))
            return _stringWidth(text,'courier',fontSize,encoding)

    _rl_accel._SWRecover(_SWRecover)
else:
    stringWidth = _slowStringWidth

def dumpFontData():
    print 'Registered Encodings:'
    keys = _encodings.keys()
    keys.sort()
    for encName in keys:
        print '   ',encName

    print
    print 'Registered Typefaces:'
    faces = _typefaces.keys()
    faces.sort()
    for faceName in faces:
        print '   ',faceName


    print
    print 'Registered Fonts:'
    k = _fonts.keys()
    k.sort()
    for key in k:
        font = _fonts[key]
        print '    %s (%s/%s)' % (font.fontName, font.face.name, font.encoding.name)



def test3widths(texts):
    # checks all 3 algorithms give same answer, note speed
    import time
    for fontName in standardFonts[0:1]:
        t0 = time.time()
        for text in texts:
            l1 = _stringWidth(text, fontName, 10)
        t1 = time.time()
        print 'fast stringWidth took %0.4f' % (t1 - t0)

        t0 = time.time()
        w = getFont(fontName).widths
        for text in texts:
            l2 = 0
            for ch in text:
                l2 = l2 + w[ord(ch)]
        t1 = time.time()
        print 'slow stringWidth took %0.4f' % (t1 - t0)

        t0 = time.time()
        for text in texts:
            l3 = getFont(fontName).stringWidth(text, 10)
        t1 = time.time()
        print 'class lookup and stringWidth took %0.4f' % (t1 - t0)
        print

def testStringWidthAlgorithms():
    rawdata = open('../../rlextra/rml2pdf/doc/rml_user_guide.prep').read()
    print 'rawdata length %d' % len(rawdata)
    print 'test one huge string...'
    test3widths([rawdata])
    print
    words = string.split(rawdata)
    print 'test %d shorter strings (average length %0.2f chars)...' % (len(words), 1.0*len(rawdata)/len(words))
    test3widths(words)


def test():
    helv = TypeFace('Helvetica')
    registerTypeFace(helv)
    print helv.glyphNames[0:30]

    wombat = TypeFace('Wombat')
    print wombat.glyphNames
    registerTypeFace(wombat)

    dumpFontData()


if __name__=='__main__':
    test()
    testStringWidthAlgorithms()
