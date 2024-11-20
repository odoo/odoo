#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/pdfbase/pdfmetrics.py
#$Header $
__version__='3.3.0'
__doc__="""This provides a database of font metric information and
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
import os, sys, encodings
from reportlab.pdfbase import _fontdata
from reportlab.lib.logger import warnOnce
from reportlab.lib.utils import rl_isfile, rl_glob, rl_isdir, open_and_read, open_and_readlines, findInPaths, isSeq, isStr
from reportlab.rl_config import defaultEncoding, T1SearchPath
from reportlab.lib.rl_accel import unicode2T1, instanceStringWidthT1
from reportlab.pdfbase import rl_codecs
_notdefChar = b'n'

rl_codecs.RL_Codecs.register()
standardFonts = _fontdata.standardFonts
standardEncodings = _fontdata.standardEncodings

_typefaces = {}
_encodings = {}
_fonts = {}
_dynFaceNames = {}      #record dynamicFont face names

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
        if lines: lines = lines[0].split('\r')
        if len(lines)<=1:
            raise ValueError('AFM file %s hasn\'t enough data' % afmFileName)
    topLevel = {}
    glyphLevel = []

    lines = [l.strip() for l in lines]
    lines = [l for l in lines if not l.lower().startswith('comment')]
    #pass 1 - get the widths
    inMetrics = 0  # os 'TOP', or 'CHARMETRICS'
    for line in lines:
        if line[0:16] == 'StartCharMetrics':
            inMetrics = 1
        elif line[0:14] == 'EndCharMetrics':
            inMetrics = 0
        elif inMetrics:
            chunks = line.split(';')
            chunks = [chunk.strip() for chunk in chunks]
            cidChunk, widthChunk, nameChunk = chunks[0:3]

            # character ID
            l, r = cidChunk.split()
            assert l == 'C', 'bad line in font file %s' % line
            cid = int(r)

            # width
            l, r = widthChunk.split()
            assert l == 'WX', 'bad line in font file %s' % line
            try:
                width = int(r)
            except ValueError:
                width = float(r)

            # name
            l, r = nameChunk.split()
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
                left, right = line.split(' ',1)
            except:
                raise ValueError("Header information error in afm %s: line='%s'" % (afmFileName, line))
            try:
                right = int(right)
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
        self.glyphNames = list(self.glyphWidths.keys())
        self.ascent,self.descent = _fontdata.ascent_descent[name]

    def getFontFiles(self):
        "Info function, return list of the font files this depends on."
        return []

    def findT1File(self, ext='.pfb'):
        possible_exts = (ext.lower(), ext.upper())
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
                if ext.lower() == '.pfb':
                    for e in possible_exts:
                        pfb = os.path.splitext(afm)[0] + e
                        if rl_isfile(pfb):
                            r = pfb
                        else:
                            r = None
                elif ext.lower() == '.afm':
                    r = afm
            else:
                r = None
        if r is None:
            warnOnce("Can't find %s for face '%s'" % (ext, self.name))
        return r

def bruteForceSearchForFile(fn,searchPath=None):
    if searchPath is None: from reportlab.rl_config import T1SearchPath as searchPath
    if rl_isfile(fn): return fn
    bfn = os.path.basename(fn)
    for dirname in searchPath:
        if not rl_isdir(dirname): continue
        tfn = os.path.join(dirname,bfn)
        if rl_isfile(tfn): return tfn
    return fn

def bruteForceSearchForAFM(faceName):
    """Looks in all AFM files on path for face with given name.

    Returns AFM file name or None.  Ouch!"""
    from reportlab.rl_config import T1SearchPath

    for dirname in T1SearchPath:
        if not rl_isdir(dirname): continue
        possibles = rl_glob(dirname + os.sep + '*.[aA][fF][mM]')
        for possible in possibles:
            try:
                topDict, glyphDict = parseAFMFile(possible)
                if topDict['FontName'] == faceName:
                    return possible
            except:
                t,v,b=sys.exc_info()
                v.args = (' '.join(map(str,v.args))+', while looking for faceName=%r' % faceName,)
                raise 


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
        elif isStr(base):
            baseEnc = getEncoding(base)
            self.baseEncodingName = baseEnc.name
            self.vector = baseEnc.vector[:]
        elif isSeq(base):
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
        return self.name==other.name and tuple(self.vector)==tuple(other.vector)

    def modifyRange(self, base, newNames):
        """Set a group of character names starting at the code point 'base'."""
        assert self.frozen == 0, 'Cannot modify a frozen encoding'
        idx = base
        for name in newNames:
            self.vector[idx] = name
            idx = idx + 1

    def getDifferences(self, otherEnc):
        """
        Return a compact list of the code points differing between two encodings

        This is in the Adobe format: list of
           [[b1, name1, name2, name3],
           [b2, name4]]
           
        where b1...bn is the starting code point, and the glyph names following
        are assigned consecutive code points.
        
        """

        ranges = []
        curRange = None
        for i in range(len(self.vector)):
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
        baseEncodingName = self.baseEncodingName
        baseEnc = getEncoding(baseEncodingName)
        differences = self.getDifferences(baseEnc) #[None] * 256)

        # if no differences, we just need the base name
        if differences == []:
            return pdfdoc.PDFName(baseEncodingName)
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
            if baseEncodingName in ('MacRomanEncoding','MacExpertEncoding','WinAnsiEncoding'):
                #https://www.adobe.com/content/dam/acom/en/devnet/acrobat/pdfs/PDF32000_2008.pdf page 263
                D["BaseEncoding"] = pdfdoc.PDFName(baseEncodingName)
            D["Type"] = pdfdoc.PDFName("Encoding")
            PD = pdfdoc.PDFDictionary(D)
            return PD

#for encName in standardEncodings:
#    registerEncoding(Encoding(encName))


standardT1SubstitutionFonts = []
class Font:
    """Represents a font (i.e combination of face and encoding).

    Defines suitable machinery for single byte fonts.  This is
    a concrete class which can handle the basic built-in fonts;
    not clear yet if embedded ones need a new font class or
    just a new typeface class (which would do the job through
    composition)"""

    _multiByte = 0      # do not want our own stringwidth
    _dynamicFont = 0    # do not want dynamic subsetting

    def __init__(self, name, faceName, encName, substitutionFonts=None):
        self.fontName = name
        face = self.face = getTypeFace(faceName)
        self.encoding= getEncoding(encName)
        self.encName = encName
        self.substitutionFonts = (standardT1SubstitutionFonts
                                    if face.builtIn and face.requiredEncoding is None
                                    else substitutionFonts or [])
        self._calcWidths()
        self._notdefChar = _notdefChar
        self._notdefFont = name=='ZapfDingbats' and self or _notdefFont

    def stringWidth(self, text, size, encoding='utf8'):
        return instanceStringWidthT1(self, text, size, encoding=encoding)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.face.name)

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
                        print('typeface "%s" does not have a glyph "%s", bad font!' % (self.face.name, glyphName))
                    else:
                        pass
        self.widths = w

    def _formatWidths(self):
        "returns a pretty block in PDF Array format to aid inspection"
        text = b'['
        for i in range(256):
            text = text + b' ' + bytes(str(self.widths[i]),'utf8')
            if i == 255:
                text = text + b' ]'
            if i % 16 == 15:
                text = text + b'\n'
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
        e = self.encoding.makePDFObject()
        if not isStr(e) or e in ('/MacRomanEncoding','/MacExpertEncoding','/WinAnsiEncoding'):
            #https://www.adobe.com/content/dam/acom/en/devnet/acrobat/pdfs/PDF32000_2008.pdf page 255
            pdfFont.Encoding = e

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

def _pfbCheck(p,d,m,fn):
    if chr(d[p])!=PFB_MARKER or chr(d[p+1])!=m:
        raise ValueError('Bad pfb file\'%s\' expected chr(%d)chr(%d) at char %d, got chr(%d)chr(%d)' % (fn,ord(PFB_MARKER),ord(m),p,d[p],d[p+1]))
    if m==PFB_EOF: return
    p = p + 2
    l = (((((d[p+3])<<8)|(d[p+2])<<8)|(d[p+1]))<<8)|(d[p])
    p = p + 4
    if p+l>len(d):
        raise ValueError('Bad pfb file\'%s\' needed %d+%d bytes have only %d!' % (fn,p,l,len(d)))
    return p, p+l

_postScriptNames2Unicode = None
class EmbeddedType1Face(TypeFace):
    """A Type 1 font other than one of the basic 14.

    Its glyph data will be embedded in the PDF file."""
    def __init__(self, afmFileName, pfbFileName):
        # ignore afm file for now
        TypeFace.__init__(self, None)
        #None is a hack, name will be supplied by AFM parse lower done
        #in this __init__ method.
        afmFileName = findInPaths(afmFileName,T1SearchPath)
        pfbFileName = findInPaths(pfbFileName,T1SearchPath)
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
        pfbFileName = bruteForceSearchForFile(pfbFileName)
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
        afmFileName = bruteForceSearchForFile(afmFileName)
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
        tokens = strBbox.split()
        self.bbox = []
        for tok in tokens:
            self.bbox.append(int(tok))

        glyphWidths = {}
        for (cid, width, name) in glyphData:
            glyphWidths[name] = width
        self.glyphWidths = glyphWidths
        self.glyphNames = list(glyphWidths.keys())
        self.glyphNames.sort()

        # for font-specific encodings like Symbol, Dingbats, Carta we
        # need to make a new encoding as well....
        if topLevel.get('EncodingScheme', None) == 'FontSpecific':
            global _postScriptNames2Unicode
            if _postScriptNames2Unicode is None:
                try:
                    from reportlab.pdfbase._glyphlist import _glyphname2unicode
                    _postScriptNames2Unicode = _glyphname2unicode
                    del _glyphname2unicode
                except:
                    _postScriptNames2Unicode = {}
                    raise ValueError(
                            "cannot import module reportlab.pdfbase._glyphlist module\n"
                            "you can obtain a version from here\n"
                            "https://www.reportlab.com/ftp/_glyphlist.py\n"
                            )

            names = [None] * 256
            ex = {}
            rex  = {}
            for (code, width, name) in glyphData:
                if 0<=code<=255:
                    names[code] = name
                    u = _postScriptNames2Unicode.get(name,None)
                    if u is not None:
                        rex[code] = u
                        ex[u] = code
            encName = encodings.normalize_encoding('rl-dynamic-%s-encoding' % self.name)
            rl_codecs.RL_Codecs.add_dynamic_codec(encName,ex,rex)
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
    if not face.name in standardFonts:
        # HACK - bold/italic do not apply for type 1, so egister
        # all combinations of mappings.
        registerFontFamily(face.name)

def registerEncoding(enc):
    assert isinstance(enc, Encoding), 'Not an Encoding: %s' % enc
    if enc.name in _encodings:
        # already got one, complain if they are not the same
        if enc.isEqual(_encodings[enc.name]):
            enc.freeze()
        else:
            raise FontError('Encoding "%s" already registered with a different name vector!' % enc.name)
    else:
        _encodings[enc.name] = enc
        enc.freeze()
    # have not yet dealt with immutability!

def registerFontFamily(family,normal=None,bold=None,italic=None,boldItalic=None):
    from reportlab.lib import fonts
    if not normal: normal = family
    family = family.lower()
    if not boldItalic: boldItalic = italic or bold or normal
    if not bold: bold = normal
    if not italic: italic = normal
    fonts.addMapping(family, 0, 0, normal)
    fonts.addMapping(family, 1, 0, bold)
    fonts.addMapping(family, 0, 1, italic)
    fonts.addMapping(family, 1, 1, boldItalic)

def registerFont(font):
    "Registers a font, including setting up info for accelerated stringWidth"
    #assert isinstance(font, Font), 'Not a Font: %s' % font
    fontName = font.fontName
    if font._dynamicFont:
        faceName = font.face.name
        if fontName not in _fonts:
            if faceName in _dynFaceNames:
                ofont = _dynFaceNames[faceName]
                if not ofont._dynamicFont:
                    raise ValueError('Attempt to register fonts %r %r for face %r' % (ofont, font, faceName))
                else:
                    _fonts[fontName] = ofont
            else:
                _dynFaceNames[faceName] = _fonts[fontName] = font
    else:
        _fonts[fontName] = font

    if font._multiByte:
        # CID fonts don't need to have typeface registered.
        #need to set mappings so it can go in a paragraph even if within
        # bold tags
        registerFontFamily(font.fontName)

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

def findFontAndRegister(fontName):
    '''search for and register a font given its name'''
    fontName = str(fontName)
    assert type(fontName) is str, 'fontName=%s is not required type str' % ascii(fontName)
    #it might have a font-specific encoding e.g. Symbol
    # or Dingbats.  If not, take the default.
    face = getTypeFace(fontName)
    if face.requiredEncoding:
        font = Font(fontName, fontName, face.requiredEncoding)
    else:
        font = Font(fontName, fontName, defaultEncoding)
    registerFont(font)
    return font

def getFont(fontName):
    """Lazily constructs known fonts if not found.

    Names of form 'face-encoding' will be built if
    face and encoding are known.  Also if the name is
    just one of the standard 14, it will make up a font
    in the default encoding."""
    try:
        return _fonts[fontName]
    except KeyError:
        return findFontAndRegister(fontName)

_notdefFont = getFont('ZapfDingbats')
standardT1SubstitutionFonts.extend([getFont('Symbol'),_notdefFont])

def getAscentDescent(fontName,fontSize=None):
    font = getFont(fontName)
    try:
        ascent = font.ascent
        descent = font.descent
    except:
        ascent = font.face.ascent
        descent = font.face.descent
    if fontSize:
        norm = fontSize/1000.
        return ascent*norm, descent*norm
    else:
        return ascent, descent

def getAscent(fontName,fontSize=None):
    return getAscentDescent(fontName,fontSize)[0]

def getDescent(fontName,fontSize=None):
    return getAscentDescent(fontName,fontSize)[1]

def getRegisteredFontNames():
    "Returns what's in there"
    reg = list(_fonts.keys())
    reg.sort()
    return reg

def stringWidth(text, fontName, fontSize, encoding='utf8'):
    """Compute width of string in points;
    not accelerated as fast enough because of instanceStringWidthT1/TTF"""
    return getFont(fontName).stringWidth(text, fontSize, encoding=encoding)

def dumpFontData():
    print('Registered Encodings:')
    keys = list(_encodings.keys())
    keys.sort()
    for encName in keys:
        print('   ',encName)

    print()
    print('Registered Typefaces:')
    faces = list(_typefaces.keys())
    faces.sort()
    for faceName in faces:
        print('   ',faceName)


    print()
    print('Registered Fonts:')
    k = list(_fonts.keys())
    k.sort()
    for key in k:
        font = _fonts[key]
        print('    %s (%s/%s)' % (font.fontName, font.face.name, font.encoding.name))

def test3widths(texts):
    # checks all 3 algorithms give same answer, note speed
    import time
    for fontName in standardFonts[0:1]:
##        t0 = time.time()
##        for text in texts:
##            l1 = stringWidth(text, fontName, 10)
##        t1 = time.time()
##        print 'fast stringWidth took %0.4f' % (t1 - t0)

        t0 = time.time()
        w = getFont(fontName).widths
        for text in texts:
            l2 = 0
            for ch in text:
                l2 = l2 + w[ord(ch)]
        t1 = time.time()
        print('slow stringWidth took %0.4f' % (t1 - t0))

        t0 = time.time()
        for text in texts:
            l3 = getFont(fontName).stringWidth(text, 10)
        t1 = time.time()
        print('class lookup and stringWidth took %0.4f' % (t1 - t0))
        print()

def testStringWidthAlgorithms():
    rawdata = open('../../rlextra/rml2pdf/doc/rml_user_guide.prep').read()
    print('rawdata length %d' % len(rawdata))
    print('test one huge string...')
    test3widths([rawdata])
    print()
    words = rawdata.split()
    print('test %d shorter strings (average length %0.2f chars)...' % (len(words), 1.0*len(rawdata)/len(words)))
    test3widths(words)


def test():
    helv = TypeFace('Helvetica')
    registerTypeFace(helv)
    print(helv.glyphNames[0:30])

    wombat = TypeFace('Wombat')
    print(wombat.glyphNames)
    registerTypeFace(wombat)

    dumpFontData()

#preserve the initial values here
def _reset(
        initial_dicts = dict(
            _typefaces = _typefaces.copy(),
            _encodings = _encodings.copy(),
            _fonts = _fonts.copy(),
            _dynFaceNames = _dynFaceNames.copy(),
            )
        ):
    for k,v in initial_dicts.items():
        d=globals()[k]
        d.clear()
        d.update(v)
    rl_codecs.RL_Codecs.reset_dynamic_codecs()

from reportlab.rl_config import register_reset
register_reset(_reset)
del register_reset

if __name__=='__main__':
    test()
    testStringWidthAlgorithms()
