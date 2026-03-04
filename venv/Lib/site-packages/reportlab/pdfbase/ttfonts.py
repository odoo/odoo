#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
__version__ = '$Id$'
__doc__="""TrueType font support

This defines classes to represent TrueType fonts.  They know how to calculate
their own width and how to write themselves into PDF files.  They support
subsetting and embedding and can represent all 16-bit Unicode characters.

Note on dynamic fonts
---------------------

Usually a Font in ReportLab corresponds to a fixed set of PDF objects (Font,
FontDescriptor, Encoding).  But with dynamic font subsetting a single TTFont
will result in a number of Font/FontDescriptor/Encoding object sets, and the
contents of those will depend on the actual characters used for printing.

To support dynamic font subsetting a concept of "dynamic font" was introduced.
Dynamic Fonts have a _dynamicFont attribute set to 1.

Dynamic fonts have the following additional functions::

    def splitString(self, text, doc):
        '''Splits text into a number of chunks, each of which belongs to a
        single subset.  Returns a list of tuples (subset, string).  Use
        subset numbers with getSubsetInternalName.  Doc is used to identify
        a document so that different documents may have different dynamically
        constructed subsets.'''

    def getSubsetInternalName(self, subset, doc):
        '''Returns the name of a PDF Font object corresponding to a given
        subset of this dynamic font.  Use this function instead of
        PDFDocument.getInternalFontName.'''

You must never call PDFDocument.getInternalFontName for dynamic fonts.

If you have a traditional static font, mapping to PDF text output operators
is simple::

   '%s 14 Tf (%s) Tj' % (getInternalFontName(psfontname), text)

If you have a dynamic font, use this instead::

   for subset, chunk in font.splitString(text, doc):
       '%s 14 Tf (%s) Tj' % (font.getSubsetInternalName(subset, doc), chunk)

(Tf is a font setting operator and Tj is a text ouput operator.  You should
also escape invalid characters in Tj argument, see TextObject._formatText.
Oh, and that 14 up there is font size.)

Canvas and TextObject have special support for dynamic fonts.
"""

from struct import pack, unpack, error as structError
from reportlab.lib.utils import bytestr, isUnicode, char2int, isStr, isBytes
from reportlab.pdfbase import pdfmetrics, pdfdoc
from reportlab import rl_config
from reportlab.lib.rl_accel import hex32, add32, calcChecksum, instanceStringWidthTTF
from collections import namedtuple
from io import BytesIO
import os, time

class TTFError(pdfdoc.PDFError):
    "TrueType font exception"
    pass

def SUBSETN(n,table=bytes.maketrans(b'0123456789',b'ABCDEFGIJK')):
    return bytes('%6.6d'%n,'ASCII').translate(table)
#
# Helpers
#
def makeToUnicodeCMap(fontname, subset):
    """Creates a ToUnicode CMap for a given subset.  See Adobe
    _PDF_Reference (ISBN 0-201-75839-3) for more information."""
    cmap = [
        "/CIDInit /ProcSet findresource begin",
        "12 dict begin",
        "begincmap",
        "/CIDSystemInfo",
        "<< /Registry (%s)" % fontname,
        "/Ordering (%s)" % fontname,
        "/Supplement 0",
        ">> def",
        "/CMapName /%s def" % fontname,
        "/CMapType 2 def",
        "1 begincodespacerange",
        "<00> <%02X>" % (len(subset) - 1),
        "endcodespacerange",
        "%d beginbfchar" % len(subset)
        ] + ["<%02X> <%04X>" % (i,v) for i,v in enumerate(subset)] + [
        "endbfchar",
        "endcmap",
        "CMapName currentdict /CMap defineresource pop",
        "end",
        "end"
        ]
    return '\n'.join(cmap)

def splice(stream, offset, value):
    """Splices the given value into stream at the given offset and
    returns the resulting stream (the original is unchanged)"""
    return stream[:offset] + value + stream[offset + len(value):]

def _set_ushort(stream, offset, value):
    """Writes the given unsigned short value into stream at the given
    offset and returns the resulting stream (the original is unchanged)"""
    return splice(stream, offset, pack(">H", value))
#
# TrueType font handling
#

GF_ARG_1_AND_2_ARE_WORDS        = 1 << 0
GF_ARGS_ARE_XY_VALUES           = 1 << 1
GF_ROUND_XY_TO_GRID             = 1 << 2
GF_WE_HAVE_A_SCALE              = 1 << 3
GF_RESERVED                     = 1 << 4
GF_MORE_COMPONENTS              = 1 << 5
GF_WE_HAVE_AN_X_AND_Y_SCALE     = 1 << 6
GF_WE_HAVE_A_TWO_BY_TWO         = 1 << 7
GF_WE_HAVE_INSTRUCTIONS         = 1 << 8
GF_USE_MY_METRICS               = 1 << 9
GF_OVERLAP_COMPOUND             = 1 << 10
GF_SCALED_COMPONENT_OFFSET      = 1 << 11
GF_UNSCALED_COMPONENT_OFFSET    = 1 << 12


_cached_ttf_dirs={}
def _ttf_dirs(*roots):
    R = _cached_ttf_dirs.get(roots,None)
    if R is None:
        join = os.path.join
        realpath = os.path.realpath
        R = []
        aR = R.append
        for root in roots:
            for r, d, f in os.walk(root,followlinks=True):
                s = realpath(r)
                if s not in R: aR(s)
                for s in d:
                    s = realpath(join(r,s))
                    if s not in R: aR(s)
        _cached_ttf_dirs[roots] = R
    return R

def TTFOpenFile(fn):
    '''Opens a TTF file possibly after searching TTFSearchPath
    returns (filename,file)
    '''
    from reportlab.lib.utils import rl_isfile, open_for_read
    try:
        f = open_for_read(fn,'rb')
        return fn, f
    except IOError:
        import os
        if not os.path.isabs(fn):
            for D in _ttf_dirs(*rl_config.TTFSearchPath):
                tfn = os.path.join(D,fn)
                if rl_isfile(tfn):
                    f = open_for_read(tfn,'rb')
                    return tfn, f
        raise TTFError('Can\'t open file "%s"' % fn)

class TTFontParser:
    "Basic TTF file parser"
    ttfVersions = (0x00010000,0x74727565,0x74746366)
    ttcVersions = (0x00010000,0x00020000)
    fileKind='TTF'

    def __init__(self, file, validate=0,subfontIndex=0):
        """Loads and parses a TrueType font file.  file can be a filename or a
        file object.  If validate is set to a false values, skips checksum
        validation.  This can save time, especially if the font is large.
        """
        self.validate = validate
        self.readFile(file)
        isCollection = self.readHeader()
        if isCollection:
            self.readTTCHeader()
            self.getSubfont(subfontIndex)
        else:
            if self.validate: self.checksumFile()
            self.readTableDirectory()
            self.subfontNameX = b''

    def readTTCHeader(self):
        self.ttcVersion = self.read_ulong()
        self.fileKind = 'TTC'
        self.ttfVersions = self.ttfVersions[:-1]
        if self.ttcVersion not in self.ttcVersions: 
            raise TTFError('"%s" is not a %s file: can\'t read version 0x%8.8x' %(self.filename,self.fileKind,self.ttcVersion))
        self.numSubfonts = self.read_ulong()
        self.subfontOffsets = []
        a = self.subfontOffsets.append
        for i in range(self.numSubfonts):
            a(self.read_ulong())

    def getSubfont(self,subfontIndex):
        if self.fileKind!='TTC':
            raise TTFError('"%s" is not a TTC file: use this method' % (self.filename,self.fileKind))
        try:
            pos = self.subfontOffsets[subfontIndex]
        except IndexError:
            raise TTFError('TTC file "%s": bad subfontIndex %s not in [0,%d]' % (self.filename,subfontIndex,self.numSubfonts-1))
        self.seek(pos)
        self.readHeader()
        self.readTableDirectory()
        self.subfontNameX = bytestr('-'+str(subfontIndex))

    def readTableDirectory(self):
        try:
            self.numTables = self.read_ushort()
            self.searchRange = self.read_ushort()
            self.entrySelector = self.read_ushort()
            self.rangeShift = self.read_ushort()

            # Read table directory
            self.table = {}
            self.tables = []
            for n in range(self.numTables):
                record = {}
                record['tag'] = self.read_tag()
                record['checksum'] = self.read_ulong()
                record['offset'] = self.read_ulong()
                record['length'] = self.read_ulong()
                self.tables.append(record)
                self.table[record['tag']] = record
        except:
            raise TTFError('Corrupt %s file "%s" cannot read Table Directory' % (self.fileKind, self.filename))
        if self.validate: self.checksumTables()

    def readHeader(self):
        '''read the sfnt header at the current position'''
        try:
            self.version = version = self.read_ulong()
        except:
            raise TTFError('"%s" is not a %s file: can\'t read version' %(self.filename,self.fileKind))

        if version==0x4F54544F:
            raise TTFError('%s file "%s": postscript outlines are not supported'%(self.fileKind,self.filename))

        if version not in self.ttfVersions:
            raise TTFError('Not a recognized TrueType font: version=0x%8.8X' % version)
        return version==self.ttfVersions[-1]

    def readFile(self,f):
        if not hasattr(self,'_ttf_data'):
            if hasattr(f,'read'):
                self.filename = getattr(f,'name','(ttf)')   #good idea Marius
                self._ttf_data = f.read()
            else:
                self.filename, f = TTFOpenFile(f)
                self._ttf_data = f.read()
                f.close()
        self._pos = 0

    def checksumTables(self):
        # Check the checksums for all tables
        for t in self.tables:
            table = self.get_chunk(t['offset'], t['length'])
            checksum = calcChecksum(table)
            if t['tag'] == 'head':
                adjustment = unpack('>l', table[8:8+4])[0]
                checksum = add32(checksum, -adjustment)
            xchecksum = t['checksum']
            if xchecksum != checksum:
                raise TTFError('TTF file "%s": invalid checksum %s table: %s (expected %s)' % (self.filename,hex32(checksum),t['tag'],hex32(xchecksum)))

    def checksumFile(self):
        # Check the checksums for the whole file
        checksum = calcChecksum(self._ttf_data)
        if 0xB1B0AFBA!=checksum:
            raise TTFError('TTF file "%s": invalid checksum %s (expected 0xB1B0AFBA) len: %d &3: %d' % (self.filename,hex32(checksum),len(self._ttf_data),(len(self._ttf_data)&3)))

    def get_table_pos(self, tag):
        "Returns the offset and size of a given TTF table."
        offset = self.table[tag]['offset']
        length = self.table[tag]['length']
        return (offset, length)

    def seek(self, pos):
        "Moves read pointer to a given offset in file."
        self._pos = pos

    def skip(self, delta):
        "Skip the given number of bytes."
        self._pos = self._pos + delta

    def seek_table(self, tag, offset_in_table = 0):
        """Moves read pointer to the given offset within a given table and
        returns absolute offset of that position in the file."""
        self._pos = self.get_table_pos(tag)[0] + offset_in_table
        return self._pos

    def read_tag(self):
        "Read a 4-character tag"
        self._pos += 4
        return str(self._ttf_data[self._pos - 4:self._pos],'utf8')

    def get_chunk(self, pos, length):
        "Return a chunk of raw data at given position"
        return bytes(self._ttf_data[pos:pos+length])

    def read_uint8(self):
        self._pos += 1
        return int(self._ttf_data[self._pos-1])

    def read_ushort(self):
        "Reads an unsigned short"
        self._pos += 2
        return unpack('>H',self._ttf_data[self._pos-2:self._pos])[0]

    def read_ulong(self):
        "Reads an unsigned long"
        self._pos += 4
        return unpack('>L',self._ttf_data[self._pos - 4:self._pos])[0]

    def read_short(self):
        "Reads a signed short"
        self._pos += 2
        try:
            return unpack('>h',self._ttf_data[self._pos-2:self._pos])[0]
        except structError as error:
            raise TTFError(error)

    def get_ushort(self, pos):
        "Return an unsigned short at given position"
        return unpack('>H',self._ttf_data[pos:pos+2])[0]

    def get_ulong(self, pos):
        "Return an unsigned long at given position"
        return unpack('>L',self._ttf_data[pos:pos+4])[0]

    def get_table(self, tag):
        "Return the given TTF table"
        pos, length = self.get_table_pos(tag)
        return self._ttf_data[pos:pos+length]

class TTFontMaker:
    "Basic TTF file generator"

    def __init__(self):
        "Initializes the generator."
        self.tables = {}

    def add(self, tag, data):
        "Adds a table to the TTF file."
        if tag == 'head':
            data = splice(data, 8, b'\0\0\0\0')
        self.tables[tag] = data

    def makeStream(self):
        "Finishes the generation and returns the TTF file as a string"
        stm = BytesIO()
        write = stm.write

        tables = self.tables
        numTables = len(tables)
        searchRange = 1
        entrySelector = 0
        while searchRange * 2 <= numTables:
            searchRange = searchRange * 2
            entrySelector = entrySelector + 1
        searchRange = searchRange * 16
        rangeShift = numTables * 16 - searchRange

        # Header
        write(pack(">lHHHH", 0x00010000, numTables, searchRange,
                                 entrySelector, rangeShift))

        # Table directory
        offset = 12 + numTables * 16
        wStr = lambda x:write(bytes(tag,'latin1'))
        tables_items = list(sorted(tables.items()))
        for tag, data in tables_items:
            if tag == 'head':
                head_start = offset
            checksum = calcChecksum(data)
            wStr(tag)
            write(pack(">LLL", checksum, offset, len(data)))
            paddedLength = (len(data)+3)&~3
            offset = offset + paddedLength

        # Table data
        for tag, data in tables_items:
            data += b"\0\0\0"
            write(data[:len(data)&~3])

        checksum = calcChecksum(stm.getvalue())
        checksum = add32(0xB1B0AFBA, -checksum)
        stm.seek(head_start + 8)
        write(pack('>L', checksum))

        return stm.getvalue()

#this is used in the cmap encoding fmt==2 case
CMapFmt2SubHeader = namedtuple('CMapFmt2SubHeader', 'firstCode entryCount idDelta idRangeOffset')

class TTFNameBytes(bytes):
    '''class used to return named strings'''
    def __new__(cls,b,enc='utf8'):
        try:
            ustr = b.decode(enc)
        except:
            ustr = b.decode('latin1')
        self = bytes.__new__(cls,ustr.encode('utf8'))
        self.ustr = ustr
        return self
    
class TTFontFile(TTFontParser):
    "TTF file parser and generator"
    _agfnc = 0
    _agfnm = {}

    def __init__(self, file, charInfo=1, validate=0,subfontIndex=0):
        """Loads and parses a TrueType font file.

        file can be a filename or a file object.  If validate is set to a false
        values, skips checksum validation.  This can save time, especially if
        the font is large.  See TTFontFile.extractInfo for more information.
        """
        if isStr(subfontIndex): #bytes or unicode
            sfi = 0
            __dict__ = self.__dict__.copy()
            while True:
                TTFontParser.__init__(self, file, validate=validate,subfontIndex=sfi)
                numSubfonts = self.numSubfonts = self.read_ulong()
                self.extractInfo(charInfo)
                if (isBytes(subfontIndex) and subfontIndex==self.name
                    or subfontIndex==self.name.ustr): #we found it
                    return
                if not sfi:
                    __dict__.update(dict(_ttf_data=self._ttf_data, filename=self.filename))
                sfi += 1
                if sfi>=numSubfonts:
                    raise ValueError('cannot find %r subfont %r' % (self.filename, subfontIndex))
                self.__dict__.clear()
                self.__dict__.update(__dict__)
        else:
            TTFontParser.__init__(self, file, validate=validate,subfontIndex=subfontIndex)
            self.extractInfo(charInfo)

    def extractInfo(self, charInfo=1):
        """
        Extract typographic information from the loaded font file.

        The following attributes will be set::
        
            name         PostScript font name
            flags        Font flags
            ascent       Typographic ascender in 1/1000ths of a point
            descent      Typographic descender in 1/1000ths of a point
            capHeight    Cap height in 1/1000ths of a point (0 if not available)
            bbox         Glyph bounding box [l,t,r,b] in 1/1000ths of a point
            _bbox        Glyph bounding box [l,t,r,b] in unitsPerEm
            unitsPerEm   Glyph units per em
            italicAngle  Italic angle in degrees ccw
            stemV        stem weight in 1/1000ths of a point (approximate)
        
        If charInfo is true, the following will also be set::
        
            defaultWidth   default glyph width in 1/1000ths of a point
            charWidths     dictionary of character widths for every supported UCS character
                           code
        
        This will only work if the font has a Unicode cmap (platform 3,
        encoding 1, format 4 or platform 0 any encoding format 4).  Setting
        charInfo to false avoids this requirement
        
        """
        # name - Naming table
        name_offset = self.seek_table("name")
        format = self.read_ushort()
        if format != 0:
            raise TTFError("Unknown name table format (%d)" % format)
        numRecords = self.read_ushort()
        string_data_offset = name_offset + self.read_ushort()
        names = {1:None,2:None,3:None,4:None,6:None}
        K = list(names.keys())
        nameCount = len(names)
        for i in range(numRecords):
            platformId = self.read_ushort()
            encodingId = self.read_ushort()
            languageId = self.read_ushort()
            nameId = self.read_ushort()
            length = self.read_ushort()
            offset = self.read_ushort()
            if nameId not in K: continue
            N = None
            if platformId == 3 and encodingId == 1 and languageId == 0x409: # Microsoft, Unicode, US English, PS Name
                opos = self._pos
                try:
                    self.seek(string_data_offset + offset)
                    if length % 2 != 0:
                        raise TTFError("PostScript name is UTF-16BE string of odd length")
                    N = TTFNameBytes(self.get_chunk(string_data_offset + offset, length),'utf_16_be')
                finally:
                    self._pos = opos
            elif platformId == 1 and encodingId == 0 and languageId == 0: # Macintosh, Roman, English, PS Name
                # According to OpenType spec, if PS name exists, it must exist
                # both in MS Unicode and Macintosh Roman formats.  Apparently,
                # you can find live TTF fonts which only have Macintosh format.
                N = TTFNameBytes(self.get_chunk(string_data_offset + offset, length),'mac_roman')
            if N and names[nameId]==None:
                names[nameId] = N
                nameCount -= 1
                if nameCount==0: break
        if names[6] is not None:
            psName = names[6]
        elif names[4] is not None:
            psName = names[4]
        # Fine, one last try before we bail.
        elif names[1] is not None:
            psName = names[1]
        else:
            psName = None

        # Don't just assume, check for None since some shoddy fonts cause crashes here...
        if not psName:
            if rl_config.autoGenerateTTFMissingTTFName:
                fn = self.filename
                if fn:
                    bfn = os.path.splitext(os.path.basename(fn))[0]
                if not fn:
                    psName = bytestr('_RL_%s_%s_TTF' % (time.time(), self.__class__._agfnc))
                    self.__class__._agfnc += 1
                else:
                    psName = self._agfnm.get(fn,'')
                    if not psName:
                        if bfn:
                            psName = bytestr('_RL_%s_TTF' % bfn)
                        else:
                            psName = bytestr('_RL_%s_%s_TTF' % (time.time(), self.__class__._agfnc))
                            self.__class__._agfnc += 1
                        self._agfnm[fn] = psName
            else:
                raise TTFError("Could not find PostScript font name")

        psName = psName.__class__(psName.replace(b" ", b"-"))  #Dinu Gherman's fix for font names with spaces

        for c in psName:
            if char2int(c)>126 or c in b' [](){}<>/%':
                raise TTFError("psName=%r contains invalid character %s" % (psName,ascii(c)))
        self.name = psName
        self.familyName = names[1] or psName
        self.styleName = names[2] or 'Regular'
        self.fullName = names[4] or psName
        self.uniqueFontID = names[3] or psName

        # head - Font header table
        try:
            self.seek_table("head")
        except:
            raise TTFError('head table not found ttf name=%s' % self.name)
        ver_maj, ver_min = self.read_ushort(), self.read_ushort()
        if ver_maj != 1:
            raise TTFError('Unknown head table version %d.%04x' % (ver_maj, ver_min))
        self.fontRevision = self.read_ushort(), self.read_ushort()

        self.skip(4)
        magic = self.read_ulong()
        if magic != 0x5F0F3CF5:
            raise TTFError('Invalid head table magic %04x' % magic)
        self.skip(2)
        self.unitsPerEm = unitsPerEm = self.read_ushort()
        scale = lambda x, unitsPerEm=unitsPerEm: x * 1000. / unitsPerEm
        self.skip(16)
        xMin = self.read_short()
        yMin = self.read_short()
        xMax = self.read_short()
        yMax = self.read_short()
        self.bbox = list(map(scale, [xMin, yMin, xMax, yMax]))
        self.skip(3*2)
        indexToLocFormat = self.read_ushort()
        glyphDataFormat = self.read_ushort()

        # OS/2 - OS/2 and Windows metrics table
        # (needs data from head table)
        subsettingAllowed = True
        if "OS/2" in self.table:
            self.seek_table("OS/2")
            version = self.read_ushort()
            self.skip(2)
            usWeightClass = self.read_ushort()
            self.skip(2)
            fsType = self.read_ushort()
            if fsType==0x0002 or (fsType & 0x0300):
                subsettingAllowed = os.path.basename(self.filename) not in rl_config.allowTTFSubsetting
            self.skip(58)   #11*2 + 10 + 4*4 + 4 + 3*2
            sTypoAscender = self.read_short()
            sTypoDescender = self.read_short()
            self.ascent = scale(sTypoAscender)      # XXX: for some reason it needs to be multiplied by 1.24--1.28
            self.descent = scale(sTypoDescender)

            if version > 1:
                self.skip(16)   #3*2 + 2*4 + 2
                sCapHeight = self.read_short()
                self.capHeight = scale(sCapHeight)
            else:
                self.capHeight = self.ascent
        else:
            # Microsoft TTFs require an OS/2 table; Apple ones do not.  Try to
            # cope.  The data is not very important anyway.
            usWeightClass = 500
            self.ascent = scale(yMax)
            self.descent = scale(yMin)
            self.capHeight = self.ascent

        # There's no way to get stemV from a TTF file short of analyzing actual outline data
        # This fuzzy formula is taken from pdflib sources, but we could just use 0 here
        self.stemV = 50 + int((usWeightClass / 65.0) ** 2)

        # post - PostScript table
        # (needs data from OS/2 table)
        self.seek_table("post")
        ver_maj, ver_min = self.read_ushort(), self.read_ushort()
        if ver_maj not in (1, 2, 3, 4):
            # Adobe/MS documents 1, 2, 2.5, 3; Apple also has 4.
            # From Apple docs it seems that we do not need to care
            # about the exact version, so if you get this error, you can
            # try to remove this check altogether.
            raise TTFError('Unknown post table version %d.%04x' % (ver_maj, ver_min))
        self.italicAngle = self.read_short() + self.read_ushort() / 65536.0
        self.underlinePosition = self.read_short()
        self.underlineThickness = self.read_short()
        isFixedPitch = self.read_ulong()

        self.flags = FF_SYMBOLIC        # All fonts that contain characters
                                        # outside the original Adobe character
                                        # set are considered "symbolic".
        if self.italicAngle!= 0:
            self.flags = self.flags | FF_ITALIC
        if usWeightClass >= 600:        # FW_REGULAR == 500, FW_SEMIBOLD == 600
            self.flags = self.flags | FF_FORCEBOLD
        if isFixedPitch:
            self.flags = self.flags | FF_FIXED
        # XXX: FF_SERIF?  FF_SCRIPT?  FF_ALLCAP?  FF_SMALLCAP?

        # hhea - Horizontal header table
        self.seek_table("hhea")
        ver_maj, ver_min = self.read_ushort(), self.read_ushort()
        if ver_maj != 1:
            raise TTFError('Unknown hhea table version %d.%04x' % (ver_maj, ver_min))
        self.skip(28)
        metricDataFormat = self.read_ushort()
        if metricDataFormat != 0:
            raise TTFError('Unknown horizontal metric data format (%d)' % metricDataFormat)
        numberOfHMetrics = self.read_ushort()
        if numberOfHMetrics == 0:
            raise TTFError('Number of horizontal metrics is 0')

        # maxp - Maximum profile table
        self.seek_table("maxp")
        ver_maj, ver_min = self.read_ushort(), self.read_ushort()
        if ver_maj != 1:
            raise TTFError('Unknown maxp table version %d.%04x' % (ver_maj, ver_min))
        self.numGlyphs = numGlyphs = self.read_ushort()
        if not subsettingAllowed:
            if self.numGlyphs>0xFF:
                raise TTFError('Font does not allow subsetting/embedding (%04X)' % fsType)
            else:
                self._full_font = True
        else:
            self._full_font = False

        if not charInfo:
            self.charToGlyph = None
            self.defaultWidth = None
            self.charWidths = None
            return

        if glyphDataFormat != 0:
            raise TTFError('Unknown glyph data format (%d)' % glyphDataFormat)

        # cmap - Character to glyph index mapping table
        cmap_offset = self.seek_table("cmap")
        cmapVersion = self.read_ushort()
        cmapTableCount = self.read_ushort()
        if cmapTableCount==0 and cmapVersion!=0:
            cmapTableCount, cmapVersion = cmapVersion, cmapTableCount
        encoffs = None
        enc = 0
        for n in range(cmapTableCount):
            platform = self.read_ushort()
            encoding = self.read_ushort()
            offset = self.read_ulong()
            if platform==3:
                enc = 1
                encoffs = offset
            elif platform==1 and encoding==0 and enc!=1:
                enc = 2
                encoffs = offset
            elif platform==1 and encoding==1:
                enc = 1
                encoffs = offset
            elif platform==0 and encoding!=5:
                enc = 1
                encoffs = offset
        if encoffs is None:
            raise TTFError('could not find a suitable cmap encoding')
        encoffs += cmap_offset
        self.seek(encoffs)
        fmt = self.read_ushort()
        self.charToGlyph = charToGlyph = {}
        glyphToChar = {}
        if fmt in (13,12,10,8):
            self.skip(2)    #padding
            length = self.read_ulong()
            lang = self.read_ulong()
        else:
            length = self.read_ushort()
            lang = self.read_ushort()
        if fmt==0:
            T = [self.read_uint8() for i in range(length-6)]
            for unichar in range(min(256,self.numGlyphs,len(T))):
                glyph = T[unichar]
                charToGlyph[unichar] = glyph
                glyphToChar.setdefault(glyph,[]).append(unichar)
        elif fmt==4:
            limit = encoffs + length
            segCount = int(self.read_ushort() / 2.0)
            self.skip(6)
            endCount = [self.read_ushort() for _ in range(segCount)]
            self.skip(2)
            startCount = [self.read_ushort() for _ in range(segCount)]
            idDelta = [self.read_short() for _ in range(segCount)]
            idRangeOffset_start = self._pos
            idRangeOffset = [self.read_ushort() for _ in range(segCount)]

            # Now it gets tricky.
            for n in range(segCount):
                for unichar in range(startCount[n], endCount[n] + 1):
                    if idRangeOffset[n] == 0:
                        glyph = (unichar + idDelta[n]) & 0xFFFF
                    else:
                        offset = (unichar - startCount[n]) * 2 + idRangeOffset[n]
                        offset = idRangeOffset_start + 2 * n + offset
                        if offset >= limit:
                            # workaround for broken fonts (like Thryomanes)
                            glyph = 0
                        else:
                            glyph = self.get_ushort(offset)
                            if glyph != 0:
                                glyph = (glyph + idDelta[n]) & 0xFFFF
                    charToGlyph[unichar] = glyph
                    glyphToChar.setdefault(glyph,[]).append(unichar)
        elif fmt==6:
            first = self.read_ushort()
            count = self.read_ushort()
            for glyph in range(first,first+count):
                unichar = self.read_ushort()
                charToGlyph[unichar] = glyph
                glyphToChar.setdefault(glyph,[]).append(unichar)
        elif fmt==10:
            first = self.read_ulong()
            count = self.read_ulong()
            for glyph in range(first,first+count):
                unichar = self.read_ushort()
                charToGlyph[unichar] = glyph
                glyphToChar.setdefault(glyph,[]).append(unichar)
        elif fmt==12:
            segCount = self.read_ulong()
            for n in range(segCount):
                start = self.read_ulong()
                end = self.read_ulong()
                inc = self.read_ulong() - start
                for unichar in range(start,end+1):
                    glyph = unichar + inc
                    charToGlyph[unichar] = glyph
                    glyphToChar.setdefault(glyph,[]).append(unichar)
        elif fmt==13:
            segCount = self.read_ulong()
            for n in range(segCount):
                start = self.read_ulong()
                end = self.read_ulong()
                gid = self.read_ulong()
                for unichar in range(start,end+1):
                    charToGlyph[unichar] = gid
                    glyphToChar.setdefault(gid,[]).append(unichar)
        elif fmt==2:
            T = [self.read_ushort() for i in range(256)]    #subheader keys
            maxSHK = max(T)
            SH = []
            for i in range(maxSHK+1):
                firstCode = self.read_ushort()
                entryCount = self.read_ushort()
                idDelta = self.read_ushort()
                idRangeOffset = (self.read_ushort()-(maxSHK-i)*8-2)>>1
                SH.append(CMapFmt2SubHeader(firstCode,entryCount,idDelta,idRangeOffset))
            #number of glyph indexes to read. it is the length of the entire subtable minus that bit we've read so far
            entryCount = (length-(self._pos-(cmap_offset+encoffs)))>>1
            glyphs = [self.read_short() for i in range(entryCount)]
            last = -1
            for unichar in range(256):
                if T[unichar]==0:
                    #Special case, single byte encoding entry, look unichar up in subhead
                    if last!=-1:
                        glyph = 0
                    elif (unichar<SH[0].firstCode or unichar>=SH[0].firstCode+SH[0].entryCount or
                            SH[0].idRangeOffset+(unichar-SH[0].firstCode)>=entryCount):
                        glyph = 0
                    else:
                        glyph = glyphs[SH[0].idRangeOffset+(unichar-SH[0].firstCode)]
                        if glyph!=0:
                            glyph += SH[0].idDelta
                    #assume the single byte codes are ascii
                    if glyph!=0 and glyph<self.numGlyphs:
                        charToGlyph[unichar] = glyph
                        glyphToChar.setdefault(glyph,[]).append(unichar)
                else:
                    k = T[unichar]
                    for j in range(SH[k].entryCount):
                        if SH[k].idRangeOffset+j>=entryCount:
                            glyph = 0
                        else:
                            glyph = glyphs[SH[k].idRangeOffset+j]
                            if glyph!= 0:
                                glyph += SH[k].idDelta
                        if glyph!=0 and glyph<self.numGlyphs:
                            enc = (unichar<<8)|(j+SH[k].firstCode)
                            charToGlyph[enc] = glyph
                            glyphToChar.setdefault(glyph,[]).append(enc)
                    if last==-1:
                        last = unichar
        else:
            raise ValueError('Unsupported cmap encoding format %d' % fmt)

        # hmtx - Horizontal metrics table
        # (needs data from hhea, maxp, and cmap tables)
        self.seek_table("hmtx")
        aw = None
        self.charWidths = charWidths = {}
        self.hmetrics = []
        for glyph in range(numberOfHMetrics):
            # advance width and left side bearing.  lsb is actually signed
            # short, but we don't need it anyway (except for subsetting)
            aw, lsb = self.read_ushort(), self.read_ushort()
            self.hmetrics.append((aw, lsb))
            aw = scale(aw)
            if glyph == 0:
                self.defaultWidth = aw
            if glyph in glyphToChar:
                for char in glyphToChar[glyph]:
                    charWidths[char] = aw
        for glyph in range(numberOfHMetrics, numGlyphs):
            # the rest of the table only lists advance left side bearings.
            # so we reuse aw set by the last iteration of the previous loop
            lsb = self.read_ushort()
            self.hmetrics.append((aw, lsb))
            if glyph in glyphToChar:
                for char in glyphToChar[glyph]:
                    charWidths[char] = aw

        # loca - Index to location
        if 'loca' not in self.table: raise TTFError('missing location table')
        self.seek_table('loca')
        self.glyphPos = []
        if indexToLocFormat == 0:
            for n in range(numGlyphs + 1):
                self.glyphPos.append(self.read_ushort() << 1)
        elif indexToLocFormat == 1:
            for n in range(numGlyphs + 1):
                self.glyphPos.append(self.read_ulong())
        else:
            raise TTFError('Unknown location table format (%d)' % indexToLocFormat)
        if 0x20 in charToGlyph:
            charToGlyph[0xa0] = charToGlyph[0x20]
            charWidths[0xa0] = charWidths[0x20]
        elif 0xa0 in charToGlyph:
            charToGlyph[0x20] = charToGlyph[0xa0]
            charWidths[0x20] = charWidths[0xa0]

    # Subsetting

    def makeSubset(self, subset):
        """Create a subset of a TrueType font"""
        output = TTFontMaker()

        # Build a mapping of glyphs in the subset to glyph numbers in
        # the original font.  Also build a mapping of UCS codes to
        # glyph values in the new font.

        # Start with 0 -> 0: "missing character"
        glyphMap = [0]                  # new glyph index -> old glyph index
        glyphSet = {0:0}                # old glyph index -> new glyph index
        codeToGlyph = {}                # unicode -> new glyph index
        for code in subset:
            if code in self.charToGlyph:
                originalGlyphIdx = self.charToGlyph[code]
            else:
                originalGlyphIdx = 0
            if originalGlyphIdx not in glyphSet:
                glyphSet[originalGlyphIdx] = len(glyphMap)
                glyphMap.append(originalGlyphIdx)
            codeToGlyph[code] = glyphSet[originalGlyphIdx]

        # Also include glyphs that are parts of composite glyphs
        start = self.get_table_pos('glyf')[0]
        n = 0
        while n < len(glyphMap):
            originalGlyphIdx = glyphMap[n]
            glyphPos = self.glyphPos[originalGlyphIdx]
            glyphLen = self.glyphPos[originalGlyphIdx + 1] - glyphPos
            n += 1
            if not glyphLen: continue
            self.seek(start + glyphPos)
            numberOfContours = self.read_short()
            if numberOfContours < 0:
                # composite glyph
                self.skip(8)
                flags = GF_MORE_COMPONENTS
                while flags & GF_MORE_COMPONENTS:
                    flags = self.read_ushort()
                    glyphIdx = self.read_ushort()
                    if glyphIdx not in glyphSet:
                        glyphSet[glyphIdx] = len(glyphMap)
                        glyphMap.append(glyphIdx)
                    if flags & GF_ARG_1_AND_2_ARE_WORDS:
                        self.skip(4)
                    else:
                        self.skip(2)
                    if flags & GF_WE_HAVE_A_SCALE:
                        self.skip(2)
                    elif flags & GF_WE_HAVE_AN_X_AND_Y_SCALE:
                        self.skip(4)
                    elif flags & GF_WE_HAVE_A_TWO_BY_TWO:
                        self.skip(8)


        # The following tables are simply copied from the original
        for tag in ('name', 'OS/2', 'cvt ', 'fpgm', 'prep'):
            try:
                output.add(tag, self.get_table(tag))
            except KeyError:
                # Apparently some of the tables are optional (cvt, fpgm, prep).
                # The lack of the required ones (name, OS/2) would have already
                # been caught before.
                pass

        # post - PostScript
        post = b"\x00\x03\x00\x00" + self.get_table('post')[4:16] + b"\x00" * 16
        output.add('post', post)

        numGlyphs = len(glyphMap)

        # hmtx - Horizontal Metrics
        hmtx = []
        for n in range(numGlyphs):
            aw, lsb = self.hmetrics[glyphMap[n]]
            hmtx.append(int(aw))
            hmtx.append(int(lsb))

        #work out n as 0 or first aw that's the start of a run
        n = len(hmtx)-2
        while n and hmtx[n]==hmtx[n-2]:
            n -= 2
        #fails when hmtx[n]!=hmtx[n-2] if there's a run it starts at n+2
        n += 2
        numberOfHMetrics = n>>1         #number of full H Metric pairs
        hmtx = hmtx[:n] + hmtx[n+1::2]  #full pairs + all the trailing lsb's

        hmtx = pack(*([">%dH" % len(hmtx)] + hmtx))
        output.add('hmtx', hmtx)

        # hhea - Horizontal Header
        hhea = self.get_table('hhea')
        hhea = _set_ushort(hhea, 34, numberOfHMetrics)
        output.add('hhea', hhea)

        # maxp - Maximum Profile
        maxp = self.get_table('maxp')
        maxp = _set_ushort(maxp, 4, numGlyphs)
        output.add('maxp', maxp)

        # cmap - Character to glyph mapping
        # XXX maybe use format 0 if possible, not 6?
        entryCount = len(subset)
        length = 10 + entryCount * 2
        cmap = [0, 1,           # version, number of tables
                1, 0, 0,12,     # platform, encoding, offset (hi,lo)
                6, length, 0,   # format, length, language
                0,
                entryCount] + \
               list(map(codeToGlyph.get, subset))
        cmap = pack(*([">%dH" % len(cmap)] + cmap))
        output.add('cmap', cmap)

        # glyf - Glyph data
        glyphData = self.get_table('glyf')
        offsets = []
        glyf = []
        pos = 0
        for n in range(numGlyphs):
            offsets.append(pos)
            originalGlyphIdx = glyphMap[n]
            glyphPos = self.glyphPos[originalGlyphIdx]
            glyphLen = self.glyphPos[originalGlyphIdx + 1] - glyphPos
            data = glyphData[glyphPos:glyphPos+glyphLen]
            # Fix references in composite glyphs
            if glyphLen > 2 and unpack(">h", data[:2])[0] < 0:
                # composite glyph
                pos_in_glyph = 10
                flags = GF_MORE_COMPONENTS
                while flags & GF_MORE_COMPONENTS:
                    flags = unpack(">H", data[pos_in_glyph:pos_in_glyph+2])[0]
                    glyphIdx = unpack(">H", data[pos_in_glyph+2:pos_in_glyph+4])[0]
                    data = _set_ushort(data, pos_in_glyph + 2, glyphSet[glyphIdx])
                    pos_in_glyph = pos_in_glyph + 4
                    if flags & GF_ARG_1_AND_2_ARE_WORDS:
                        pos_in_glyph = pos_in_glyph + 4
                    else:
                        pos_in_glyph = pos_in_glyph + 2
                    if flags & GF_WE_HAVE_A_SCALE:
                        pos_in_glyph = pos_in_glyph + 2
                    elif flags & GF_WE_HAVE_AN_X_AND_Y_SCALE:
                        pos_in_glyph = pos_in_glyph + 4
                    elif flags & GF_WE_HAVE_A_TWO_BY_TWO:
                        pos_in_glyph = pos_in_glyph + 8
            glyf.append(data)
            pos = pos + glyphLen
            if pos % 4 != 0:
                padding = 4 - pos % 4
                glyf.append(b'\0' * padding)
                pos = pos + padding
        offsets.append(pos)
        output.add('glyf', b''.join(glyf))

        # loca - Index to location
        loca = []
        if (pos + 1) >> 1 > 0xFFFF:
            indexToLocFormat = 1        # long format
            for offset in offsets:
                loca.append(offset)
            loca = pack(*([">%dL" % len(loca)] + loca))
        else:
            indexToLocFormat = 0        # short format
            for offset in offsets:
                loca.append(offset >> 1)
            loca = pack(*([">%dH" % len(loca)] + loca))
        output.add('loca', loca)

        # head - Font header
        head = self.get_table('head')
        head = _set_ushort(head, 50, indexToLocFormat)
        output.add('head', head)

        return output.makeStream()


#
# TrueType font embedding
#

# PDF font flags (see PDF Reference Guide table 5.19)
FF_FIXED        = 1 <<  1-1
FF_SERIF        = 1 <<  2-1
FF_SYMBOLIC     = 1 <<  3-1
FF_SCRIPT       = 1 <<  4-1
FF_NONSYMBOLIC  = 1 <<  6-1
FF_ITALIC       = 1 <<  7-1
FF_ALLCAP       = 1 << 17-1
FF_SMALLCAP     = 1 << 18-1
FF_FORCEBOLD    = 1 << 19-1

class TTFontFace(TTFontFile, pdfmetrics.TypeFace):
    """TrueType typeface.

    Conceptually similar to a single byte typeface, but the glyphs are
    identified by UCS character codes instead of glyph names."""

    def __init__(self, filename, validate=0, subfontIndex=0):
        "Loads a TrueType font from filename."
        pdfmetrics.TypeFace.__init__(self, None)
        TTFontFile.__init__(self, filename, validate=validate, subfontIndex=subfontIndex)

    def getCharWidth(self, code):
        "Returns the width of character U+<code>"
        return self.charWidths.get(code, self.defaultWidth)

    def addSubsetObjects(self, doc, fontname, subset):
        """Generate a TrueType font subset and add it to the PDF document.
        Returns a PDFReference to the new FontDescriptor object."""

        fontFile = pdfdoc.PDFStream()
        fontFile.content = self.makeSubset(subset)
        fontFile.dictionary['Length1'] = len(fontFile.content)
        if doc.compression:
            fontFile.filters = [pdfdoc.PDFZCompress]
        fontFileRef = doc.Reference(fontFile, 'fontFile:%s(%s)' % (self.filename, fontname))

        flags = self.flags & ~ FF_NONSYMBOLIC
        flags = flags | FF_SYMBOLIC

        fontDescriptor = pdfdoc.PDFDictionary({
            'Type': '/FontDescriptor',
            'Ascent': self.ascent,
            'CapHeight': self.capHeight,
            'Descent': self.descent,
            'Flags': flags,
            'FontBBox': pdfdoc.PDFArray(self.bbox),
            'FontName': pdfdoc.PDFName(fontname),
            'ItalicAngle': self.italicAngle,
            'StemV': self.stemV,
            'FontFile2': fontFileRef,
            'MissingWidth': self.defaultWidth,
            })
        return doc.Reference(fontDescriptor, 'fontDescriptor:' + fontname)

class TTEncoding:
    """Encoding for TrueType fonts (always UTF-8).

    TTEncoding does not directly participate in PDF object creation, since
    we need a number of different 8-bit encodings for every generated font
    subset.  TTFont itself cares about that."""

    def __init__(self):
        self.name = "UTF-8"

class TTFont:
    """Represents a TrueType font.

    Its encoding is always UTF-8.

    Note: you cannot use the same TTFont object for different documents
    at the same time.

    Example of usage:

        font = ttfonts.TTFont('PostScriptFontName', '/path/to/font.ttf')
        pdfmetrics.registerFont(font)

        canvas.setFont('PostScriptFontName', size)
        canvas.drawString(x, y, "Some text encoded in UTF-8")
    """
    class State:
        namePrefix = 'F'
        def __init__(self,asciiReadable=None,ttf=None):
            A = self.assignments = {}   #maps unicode to subset and index
            self.nextCode = 0
            self.internalName = None
            self.frozen = 0
            face = getattr(ttf,'face',None)
            if getattr(face,'_full_font',None):
                C = set(face.charToGlyph.keys())
                if 0xa0 in C: C.remove(0xa0)
                for n in range(256):
                    if n in C:
                        A[n] = n
                        C.remove(n)
                for n in C:
                    A[n] = n
                self.subsets = [[n for n in A]]
                self.frozen = True
                return

            if asciiReadable is None:
                asciiReadable = rl_config.ttfAsciiReadable

            if asciiReadable:
                # Let's add the first 128 unicodes to the 0th subset, so ' '
                # always has code 32 (for word spacing to work) and the ASCII
                # output is readable
                #simple asciiReadable setup
                subset0 = list(range(32,128))   #assume we have all of ASCII
                charToGlyph = getattr(face,'charToGlyph',None)
                if charToGlyph:
                    for n in subset0:
                        if n in charToGlyph:
                            A[n] = n
                else:
                    for n in subset0:
                        A[n] = n
                A[0] = 0
                self.subsets = [32*[0] + subset0]
                self.nextCode = 1   #if doing fillin of [1-31]
                #self.nextCode = 128 #if not doing fillin
            else:
                self.subsets = [[0]+[32]*32]
                A[0] = 0
                self.nextCode = 1
                A[32] = 32

    _multiByte = 1      # We want our own stringwidth
    _dynamicFont = 1    # We want dynamic subsetting

    def __init__(self, name, filename, validate=0, subfontIndex=0,asciiReadable=None):
        """Loads a TrueType font from filename.

        If validate is set to a false values, skips checksum validation.  This
        can save time, especially if the font is large.
        """
        self.fontName = name
        self.face = TTFontFace(filename, validate=validate, subfontIndex=subfontIndex)
        self.encoding = TTEncoding()
        from weakref import WeakKeyDictionary
        self.state = WeakKeyDictionary()
        if asciiReadable is None:
            asciiReadable = rl_config.ttfAsciiReadable
        self._asciiReadable = asciiReadable

    def stringWidth(self,text,size,encoding='utf8'):
        return instanceStringWidthTTF(self,text,size,encoding)

    def _assignState(self,doc,asciiReadable=None,namePrefix=None):
        '''convenience function for those wishing to roll their own state properties'''
        if asciiReadable is None:
            asciiReadable = self._asciiReadable
        try:
            state = self.state[doc]
        except KeyError:
            state = self.state[doc] = TTFont.State(asciiReadable,self)
            if namePrefix is not None:
                state.namePrefix = namePrefix
        return state

    def splitString(self, text, doc, encoding='utf-8'):
        """Splits text into a number of chunks, each of which belongs to a
        single subset.  Returns a list of tuples (subset, string).  Use subset
        numbers with getSubsetInternalName.  Doc is needed for distinguishing
        subsets when building different documents at the same time."""
        asciiReadable = self._asciiReadable
        try: state = self.state[doc]
        except KeyError: state = self.state[doc] = TTFont.State(asciiReadable,self)
        _31skip = 31 if asciiReadable and state.nextCode<32 else -256
        curSet = -1
        cur = []
        results = []
        if not isUnicode(text):
            text = text.decode('utf-8')     # encoding defaults to utf-8
        charToGlyph = self.face.charToGlyph
        assignments = state.assignments
        subsets = state.subsets
        #reserveTTFNotdef = rl_config.reserveTTFNotdef we ignore this now
        for code in map(ord,text):
            if code==0xa0: code = 32    #map nbsp into space
            if code in assignments:
                n = assignments[code]
            elif code not in charToGlyph:
                n = 0
            else:
                if state.frozen:
                    raise pdfdoc.PDFError("Font %s is already frozen, cannot add new character U+%04X" % (self.fontName, code))
                n = state.nextCode
                if n&0xFF==32:
                    # make code 32 always be a space character
                    if n!=32: subsets[n >> 8].append(32)
                    state.nextCode += 1
                    n = state.nextCode
                if n>32:
                    if not(n&0xFF):
                        subsets.append([0]) #force code 0 in as notdef
                        state.nextCode += 1
                        n = state.nextCode
                    subsets[n >> 8].append(code)
                else:
                    if n==_31skip:
                        #we heve filled in first part of subsets[0] skip past subset[32:127]
                        #this code will be executed once if asciiReadable
                        state.nextCode = 127
                    subsets[0][n] = code
                state.nextCode += 1
                assignments[code] = n
                #subsets[n>>8].append(code)
            if (n >> 8) != curSet:
                if cur:
                    results.append((curSet,bytes(cur)))
                curSet = (n >> 8)
                cur = []
            cur.append(n & 0xFF)
        if cur:
            results.append((curSet,bytes(cur)))
        return results

    def getSubsetInternalName(self, subset, doc):
        """Returns the name of a PDF Font object corresponding to a given
        subset of this dynamic font.  Use this function instead of
        PDFDocument.getInternalFontName."""
        try: state = self.state[doc]
        except KeyError: state = self.state[doc] = TTFont.State(self._asciiReadable)
        if subset < 0 or subset >= len(state.subsets):
            raise IndexError('Subset %d does not exist in font %s' % (subset, self.fontName))
        if state.internalName is None:
            state.internalName = state.namePrefix +repr(len(doc.fontMapping) + 1)
            doc.fontMapping[self.fontName] = '/' + state.internalName
            doc.delayedFonts.append(self)
        return '/%s+%d' % (state.internalName, subset)

    def addObjects(self, doc):
        """Makes  one or more PDF objects to be added to the document.  The
        caller supplies the internal name to be used (typically F1, F2, ... in
        sequence).

        This method creates a number of Font and FontDescriptor objects.  Every
        FontDescriptor is a (no more than) 256 character subset of the original
        TrueType font."""
        try: state = self.state[doc]
        except KeyError: state = self.state[doc] = TTFont.State(self._asciiReadable)
        state.frozen = 1
        for n,subset in enumerate(state.subsets):
            internalName = self.getSubsetInternalName(n, doc)[1:]
            baseFontName = (b''.join((SUBSETN(n),b'+',self.face.name,self.face.subfontNameX))).decode('pdfdoc')

            pdfFont = pdfdoc.PDFTrueTypeFont()
            pdfFont.__Comment__ = 'Font %s subset %d' % (self.fontName, n)
            pdfFont.Name = internalName
            pdfFont.BaseFont = baseFontName

            pdfFont.FirstChar = 0
            pdfFont.LastChar = len(subset) - 1

            widths = list(map(self.face.getCharWidth, subset))
            pdfFont.Widths = pdfdoc.PDFArray(widths)

            cmapStream = pdfdoc.PDFStream()
            cmapStream.content = makeToUnicodeCMap(baseFontName, subset)
            if doc.compression:
                cmapStream.filters = [pdfdoc.PDFZCompress]
            pdfFont.ToUnicode = doc.Reference(cmapStream, 'toUnicodeCMap:' + baseFontName)

            pdfFont.FontDescriptor = self.face.addSubsetObjects(doc, baseFontName, subset)

            # link it in
            ref = doc.Reference(pdfFont, internalName)
            fontDict = doc.idToObject['BasicFonts'].dict
            fontDict[internalName] = pdfFont
        del self.state[doc]

#preserve the initial values here
def _reset():
    _cached_ttf_dirs.clear()

from reportlab.rl_config import register_reset
register_reset(_reset)
del register_reset
