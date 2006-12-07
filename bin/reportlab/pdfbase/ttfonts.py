#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/pdfbase/ttfonts.py
"""TrueType font support

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
Dynamic Fonts have a _dynamicFont attribute set to 1.  Since other Font object
may lack a this attribute, you should use constructs like

    if getattr(font, '_dynamicFont', 0):
        # dynamic font
    else:
        # traditional static font

Dynamic fonts have the following additional functions:

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
is simple:

   '%s 14 Tf (%s) Tj' % (getInternalFontName(psfontname), text)

If you have a dynamic font, use this instead:

   for subset, chunk in font.splitString(text, doc):
       '%s 14 Tf (%s) Tj' % (font.getSubsetInternalName(subset, doc), chunk)

(Tf is a font setting operator and Tj is a text ouput operator.  You should
also escape invalid characters in Tj argument, see TextObject._formatText.
Oh, and that 14 up there is font size.)

Canvas and TextObject have special support for dynamic fonts.
"""

__version__ = '$Id$'

import string
from types import StringType
from struct import pack, unpack
from cStringIO import StringIO
from reportlab.pdfbase import pdfmetrics, pdfdoc

def _L2U32(L):
    return unpack('l',pack('L',L))[0]

class TTFError(pdfdoc.PDFError):
    "TrueType font exception"
    pass

#
# Helpers
#

from codecs import utf_8_encode, utf_8_decode, latin_1_decode
parse_utf8=lambda x, decode=utf_8_decode: map(ord,decode(x)[0])
parse_latin1 = lambda x, decode=latin_1_decode: map(ord,decode(x)[0])
def latin1_to_utf8(text):
    "helper to convert when needed from latin input"
    return utf_8_encode(latin_1_decode(text)[0])[0]

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
    ] + map(lambda n, subset=subset: "<%02X> <%04X>" % (n, subset[n]),
            range(len(subset))) + [
        "endbfchar",
        "endcmap",
        "CMapName currentdict /CMap defineresource pop",
        "end",
        "end"
    ]
    return string.join(cmap, "\n")

def splice(stream, offset, value):
    """Splices the given value into stream at the given offset and
    returns the resulting stream (the original is unchanged)"""
    return stream[:offset] + value + stream[offset + len(value):]

def _set_ushort(stream, offset, value):
    """Writes the given unsigned short value into stream at the given
    offset and returns the resulting stream (the original is unchanged)"""
    return splice(stream, offset, pack(">H", value))

import sys
try:
    import _rl_accel
except ImportError:
    try:
        from reportlab.lib import _rl_accel
    except ImportError:
        _rl_accel = None

try:
    hex32 = _rl_accel.hex32
except:
    def hex32(i):
        return '0X%8.8X' % (long(i)&0xFFFFFFFFL)
try:
    add32 = _rl_accel.add32
except:
    if sys.hexversion>=0x02030000:
        def add32(x, y):
            "Calculate (x + y) modulo 2**32"
            return _L2U32((long(x)+y) & 0xffffffffL)
    else:
        def add32(x, y):
            "Calculate (x + y) modulo 2**32"
            lo = (x & 0xFFFF) + (y & 0xFFFF)
            hi = (x >> 16) + (y >> 16) + (lo >> 16)
            return (hi << 16) | (lo & 0xFFFF)

try:
    calcChecksum = _rl_accel.calcChecksum
except:
    def calcChecksum(data):
        """Calculates PDF-style checksums"""
        if len(data)&3: data = data + (4-(len(data)&3))*"\0"
        sum = 0
        for n in unpack(">%dl" % (len(data)>>2), data):
            sum = add32(sum,n)
        return sum
del _rl_accel, sys
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
            from reportlab import rl_config
            for D in rl_config.TTFSearchPath:
                tfn = os.path.join(D,fn)
                if rl_isfile(tfn):
                    f = open_for_read(tfn,'rb')
                    return tfn, f
        raise TTFError('Can\'t open file "%s"' % fn)

class TTFontParser:
    "Basic TTF file parser"

    def __init__(self, file, validate=0):
        """Loads and parses a TrueType font file.  file can be a filename or a
        file object.  If validate is set to a false values, skips checksum
        validation.  This can save time, especially if the font is large.
        """

        # Open the file
        if type(file) is StringType:
            self.filename, file = TTFOpenFile(file)
        else:
            self.filename = '(ttf)'

        self._ttf_data = file.read()
        self._pos = 0

        # Read header
        try:
            version = self.read_ulong()
            if version == 0x4F54544F:
                raise TTFError, 'OpenType fonts with PostScript outlines are not supported'
            if version != 0x00010000 and version != 0x74727565:
                raise TTFError, 'Not a TrueType font'
        except:
            raise TTFError, 'Not a TrueType font'

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
            raise TTFError, 'Corrupt TrueType font file'

        if not validate:
            return

        # Check the checksums for the whole file
        checkSum = calcChecksum(self._ttf_data)
        if add32(_L2U32(0xB1B0AFBAL), -checkSum) != 0:
            raise TTFError, 'Invalid checksum %s len: %d &3: %d' % (hex32(checkSum),len(self._ttf_data),(len(self._ttf_data)&3))

        # Check the checksums for all tables
        for t in self.tables:
            table = self.get_chunk(t['offset'], t['length'])
            checkSum = calcChecksum(table)
            if t['tag'] == 'head':
                adjustment = unpack('>l', table[8:8+4])[0]
                checkSum = add32(checkSum, -adjustment)
            if t['checksum'] != checkSum:
                raise TTFError, 'Invalid checksum %s table: %s' % (hex32(checkSum),t['tag'])

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
        self._pos = self._pos + 4
        return self._ttf_data[self._pos - 4:self._pos]

    def read_ushort(self):
        "Reads an unsigned short"
        self._pos = self._pos + 2
        return (ord(self._ttf_data[self._pos - 2]) << 8) + \
               (ord(self._ttf_data[self._pos - 1]))

    def read_ulong(self):
        "Reads an unsigned long"
        self._pos = self._pos + 4
        return unpack('>l',self._ttf_data[self._pos - 4:self._pos])[0]

    def read_short(self):
        "Reads a signed short"
        us = self.read_ushort()
        if us >= 0x8000:
            return us - 0x10000
        else:
            return us

    def get_ushort(self, pos):
        "Return an unsigned short at given position"
        return (ord(self._ttf_data[pos]) << 8) + \
               (ord(self._ttf_data[pos + 1]))

    def get_ulong(self, pos):
        "Return an unsigned long at given position"
        return unpack('>l',self._ttf_data[pos:pos+4])[0]

    def get_chunk(self, pos, length):
        "Return a chunk of raw data at given position"
        return self._ttf_data[pos:pos+length]

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
            data = splice(data, 8, '\0\0\0\0')
        self.tables[tag] = data

    def makeStream(self):
        "Finishes the generation and returns the TTF file as a string"
        stm = StringIO()

        numTables = len(self.tables)
        searchRange = 1
        entrySelector = 0
        while searchRange * 2 <= numTables:
            searchRange = searchRange * 2
            entrySelector = entrySelector + 1
        searchRange = searchRange * 16
        rangeShift = numTables * 16 - searchRange

        # Header
        stm.write(pack(">lHHHH", 0x00010000, numTables, searchRange,
                                 entrySelector, rangeShift))

        # Table directory
        tables = self.tables.items()
        tables.sort()     # XXX is this the correct order?
        offset = 12 + numTables * 16
        for tag, data in tables:
            if tag == 'head':
                head_start = offset
            checksum = calcChecksum(data)
            stm.write(tag)
            stm.write(pack(">LLL", checksum, offset, len(data)))
            paddedLength = (len(data)+3)&~3
            offset = offset + paddedLength

        # Table data
        for tag, data in tables:
            data = data + "\0\0\0"
            stm.write(data[:len(data)&~3])

        checksum = calcChecksum(stm.getvalue())
        checksum = add32(_L2U32(0xB1B0AFBAL), -checksum)
        stm.seek(head_start + 8)
        stm.write(pack('>L', checksum))

        return stm.getvalue()

class TTFontFile(TTFontParser):
    "TTF file parser and generator"

    def __init__(self, file, charInfo=1, validate=0):
        """Loads and parses a TrueType font file.

        file can be a filename or a file object.  If validate is set to a false
        values, skips checksum validation.  This can save time, especially if
        the font is large.  See TTFontFile.extractInfo for more information.
        """
        TTFontParser.__init__(self, file, validate=validate)
        self.extractInfo(charInfo)

    def extractInfo(self, charInfo=1):
        """Extract typographic information from the loaded font file.

        The following attributes will be set:
            name         - PostScript font name
            flags        - Font flags
            ascent       - Typographic ascender in 1/1000ths of a point
            descent      - Typographic descender in 1/1000ths of a point
            capHeight    - Cap height in 1/1000ths of a point (0 if not available)
            bbox         - Glyph bounding box [l,t,r,b] in 1/1000ths of a point
            italicAngle  - Italic angle in degrees ccw
            stemV        - stem weight in 1/1000ths of a point (approximate)
        If charInfo is true, the following will also be set:
            defaultWidth - default glyph width in 1/1000ths of a point
            charWidths   - dictionary of character widths for every supported
                           UCS character code

        This will only work if the font has a Unicode cmap (platform 3,
        encoding 1, format 4 or platform 0 any encoding format 4).  Setting
        charInfo to false avoids this requirement.
        """
        # name - Naming table
        name_offset = self.seek_table("name")
        format = self.read_ushort()
        if format != 0:
            raise TTFError, "Unknown name table format (%d)" % format
        numRecords = self.read_ushort()
        string_data_offset = name_offset + self.read_ushort()
        names = {1:None,2:None,3:None,4:None,6:None}
        K = names.keys()
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
                self.seek(string_data_offset + offset)
                if length % 2 != 0:
                    raise TTFError, "PostScript name is UTF-16BE string of odd length"
                length /= 2
                N = []
                A = N.append
                while length > 0:
                    char = self.read_ushort()
                    A(chr(char))
                    length -= 1
                N = ''.join(N)
            elif platformId == 1 and encodingId == 0 and languageId == 0: # Macintosh, Roman, English, PS Name
                # According to OpenType spec, if PS name exists, it must exist
                # both in MS Unicode and Macintosh Roman formats.  Apparently,
                # you can find live TTF fonts which only have Macintosh format.
                N = self.get_chunk(string_data_offset + offset, length)
            if N and names[nameId]==None:
                names[nameId] = N
                nameCount -= 1
                if nameCount==0: break
        psName = names[6]
        if not psName:
            raise TTFError, "Could not find PostScript font name"
        for c in psName:
            oc = ord(c)
            if oc<33 or oc>126 or c in ('[', ']', '(', ')', '{', '}', '<', '>', '/', '%'):
                raise TTFError, "psName contains invalid character '%s' ie U+%04X" % (c,ord(c))
        self.name = psName
        self.familyName = names[1] or psName
        self.styleName = names[2] or 'Regular'
        self.fullName = names[4] or psName
        self.uniqueFontID = names[3] or psName

        # head - Font header table
        self.seek_table("head")
        ver_maj, ver_min = self.read_ushort(), self.read_ushort()
        if ver_maj != 1:
            raise TTFError, 'Unknown head table version %d.%04x' % (ver_maj, ver_min)
        self.skip(8)
        magic = self.read_ulong()
        if magic != 0x5F0F3CF5:
            raise TTFError, 'Invalid head table magic %04x' % magic
        self.skip(2)
        unitsPerEm = self.read_ushort()
        scale = lambda x, unitsPerEm=unitsPerEm: x * 1000 / unitsPerEm
        self.skip(16)
        xMin = self.read_short()
        yMin = self.read_short()
        xMax = self.read_short()
        yMax = self.read_short()
        self.bbox = map(scale, [xMin, yMin, xMax, yMax])
        self.skip(3*2)
        indexToLocFormat = self.read_ushort()
        glyphDataFormat = self.read_ushort()

        # OS/2 - OS/2 and Windows metrics table
        # (needs data from head table)
        if self.table.has_key("OS/2"):
            self.seek_table("OS/2")
            version = self.read_ushort()
            self.skip(2)
            usWeightClass = self.read_ushort()
            self.skip(2)
            fsType = self.read_ushort()
            if fsType == 0x0002 or (fsType & 0x0300) != 0:
                raise TTFError, 'Font does not allow subsetting/embedding (%04X)' % fsType
            self.skip(11*2 + 10 + 4*4 + 4 + 3*2)
            sTypoAscender = self.read_short()
            sTypoDescender = self.read_short()
            self.ascent = scale(sTypoAscender)      # XXX: for some reason it needs to be multiplied by 1.24--1.28
            self.descent = scale(sTypoDescender)

            if version > 1:
                self.skip(3*2 + 2*4 + 2)
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
            raise TTFError, 'Unknown post table version %d.%04x' % (ver_maj, ver_min)
        self.italicAngle = self.read_short() + self.read_ushort() / 65536.0
        self.skip(2*2)
        isFixedPitch = self.read_ulong()

        self.flags = FF_SYMBOLIC        # All fonts that contain characters
                                        # outside the original Adobe character
                                        # set are considered "symbolic".
        if self.italicAngle != 0:
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
            raise TTFError, 'Unknown hhea table version %d.%04x' % (ver_maj, ver_min)
        self.skip(28)
        metricDataFormat = self.read_ushort()
        if metricDataFormat != 0:
            raise TTFError, 'Unknown horizontal metric data format (%d)' % metricDataFormat
        numberOfHMetrics = self.read_ushort()
        if numberOfHMetrics == 0:
            raise TTFError, 'Number of horizontal metrics is 0'

        # maxp - Maximum profile table
        self.seek_table("maxp")
        ver_maj, ver_min = self.read_ushort(), self.read_ushort()
        if ver_maj != 1:
            raise TTFError, 'Unknown maxp table version %d.%04x' % (ver_maj, ver_min)
        numGlyphs = self.read_ushort()

        if not charInfo:
            self.charToGlyph = None
            self.defaultWidth = None
            self.charWidths = None
            return

        if glyphDataFormat != 0:
            raise TTFError, 'Unknown glyph data format (%d)' % glyphDataFormat

        # cmap - Character to glyph index mapping table
        cmap_offset = self.seek_table("cmap")
        self.skip(2)
        cmapTableCount = self.read_ushort()
        unicode_cmap_offset = None
        for n in range(cmapTableCount):
            platformID = self.read_ushort()
            encodingID = self.read_ushort()
            offset = self.read_ulong()
            if platformID == 3 and encodingID == 1: # Microsoft, Unicode
                format = self.get_ushort(cmap_offset + offset)
                if format == 4:
                    unicode_cmap_offset = cmap_offset + offset
                    break
            elif platformID == 0: # Unicode -- assume all encodings are compatible
                format = self.get_ushort(cmap_offset + offset)
                if format == 4:
                    unicode_cmap_offset = cmap_offset + offset
                    break
        if unicode_cmap_offset is None:
            raise TTFError, 'Font does not have cmap for Unicode (platform 3, encoding 1, format 4 or platform 0 any encoding format 4)'
        self.seek(unicode_cmap_offset + 2)
        length = self.read_ushort()
        limit = unicode_cmap_offset + length
        self.skip(2)
        segCount = self.read_ushort() / 2
        self.skip(6)
        endCount = map(lambda x, self=self: self.read_ushort(), range(segCount))
        self.skip(2)
        startCount = map(lambda x, self=self: self.read_ushort(), range(segCount))
        idDelta = map(lambda x, self=self: self.read_short(), range(segCount))
        idRangeOffset_start = self._pos
        idRangeOffset = map(lambda x, self=self: self.read_ushort(), range(segCount))

        # Now it gets tricky.
        glyphToChar = {}
        charToGlyph = {}
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
                if glyphToChar.has_key(glyph):
                    glyphToChar[glyph].append(unichar)
                else:
                    glyphToChar[glyph] = [unichar]
        self.charToGlyph = charToGlyph

        # hmtx - Horizontal metrics table
        # (needs data from hhea, maxp, and cmap tables)
        self.seek_table("hmtx")
        aw = None
        self.charWidths = {}
        self.hmetrics = []
        for glyph in range(numberOfHMetrics):
            # advance width and left side bearing.  lsb is actually signed
            # short, but we don't need it anyway (except for subsetting)
            aw, lsb = self.read_ushort(), self.read_ushort()
            self.hmetrics.append((aw, lsb))
            aw = scale(aw)
            if glyph == 0:
                self.defaultWidth = aw
            if glyphToChar.has_key(glyph):
                for char in glyphToChar[glyph]:
                    self.charWidths[char] = aw
        for glyph in range(numberOfHMetrics, numGlyphs):
            # the rest of the table only lists advance left side bearings.
            # so we reuse aw set by the last iteration of the previous loop
            lsb = self.read_ushort()
            self.hmetrics.append((aw, lsb))
            if glyphToChar.has_key(glyph):
                for char in glyphToChar[glyph]:
                    self.charWidths[char] = aw

        # loca - Index to location
        self.seek_table('loca')
        self.glyphPos = []
        if indexToLocFormat == 0:
            for n in range(numGlyphs + 1):
                self.glyphPos.append(self.read_ushort() << 1)
        elif indexToLocFormat == 1:
            for n in range(numGlyphs + 1):
                self.glyphPos.append(self.read_ulong())
        else:
            raise TTFError, 'Unknown location table format (%d)' % indexToLocFormat

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
            if self.charToGlyph.has_key(code):
                originalGlyphIdx = self.charToGlyph[code]
            else:
                originalGlyphIdx = 0
            if not glyphSet.has_key(originalGlyphIdx):
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
            self.seek(start + glyphPos)
            numberOfContours = self.read_short()
            if numberOfContours < 0:
                # composite glyph
                self.skip(8)
                flags = GF_MORE_COMPONENTS
                while flags & GF_MORE_COMPONENTS:
                    flags = self.read_ushort()
                    glyphIdx = self.read_ushort()
                    if not glyphSet.has_key(glyphIdx):
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
            n = n + 1

        numGlyphs = n = len(glyphMap)
        while n > 1 and self.hmetrics[n][0] == self.hmetrics[n - 1][0]:
            n = n - 1
        numberOfHMetrics = n

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
        post = "\x00\x03\x00\x00" + self.get_table('post')[4:16] + "\x00" * 16
        output.add('post', post)

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
               map(codeToGlyph.get, subset)
        cmap = apply(pack, [">%dH" % len(cmap)] + cmap)
        output.add('cmap', cmap)

        # hmtx - Horizontal Metrics
        hmtx = []
        for n in range(numGlyphs):
            originalGlyphIdx = glyphMap[n]
            aw, lsb = self.hmetrics[originalGlyphIdx]
            if n < numberOfHMetrics:
                hmtx.append(aw)
            hmtx.append(lsb)
        hmtx = apply(pack, [">%dH" % len(hmtx)] + hmtx)
        output.add('hmtx', hmtx)

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
                glyf.append('\0' * padding)
                pos = pos + padding
        offsets.append(pos)
        output.add('glyf', string.join(glyf, ""))

        # loca - Index to location
        loca = []
        if (pos + 1) >> 1 > 0xFFFF:
            indexToLocFormat = 1        # long format
            for offset in offsets:
                loca.append(offset)
            loca = apply(pack, [">%dL" % len(loca)] + loca)
        else:
            indexToLocFormat = 0        # short format
            for offset in offsets:
                loca.append(offset >> 1)
            loca = apply(pack, [">%dH" % len(loca)] + loca)
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

    def __init__(self, filename, validate=0):
        "Loads a TrueType font from filename."
        pdfmetrics.TypeFace.__init__(self, None)
        TTFontFile.__init__(self, filename, validate=validate)

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
        def __init__(self):
            self.assignments = {}
            self.nextCode = 0
            self.subsets = []
            self.internalName = None
            self.frozen = 0

    def __init__(self, name, filename, validate=0):
        """Loads a TrueType font from filename.

        If validate is set to a false values, skips checksum validation.  This
        can save time, especially if the font is large.
        """
        self.fontName = name
        self.face = TTFontFace(filename, validate=validate)
        self.encoding = TTEncoding()
        self._multiByte = 1     # We want our own stringwidth
        self._dynamicFont = 1   # We want dynamic subsetting
        self.state = {}

    def stringWidth(self, text, size):
        "Calculate text width"
        width = self.face.getCharWidth
        w = 0
        for code in parse_utf8(text):
            w = w + width(code)
        return 0.001 * w * size

    def splitString(self, text, doc):
        """Splits text into a number of chunks, each of which belongs to a
        single subset.  Returns a list of tuples (subset, string).  Use subset
        numbers with getSubsetInternalName.  Doc is needed for distinguishing
        subsets when building different documents at the same time."""
        try: state = self.state[doc]
        except KeyError: state = self.state[doc] = TTFont.State()
        curSet = -1
        cur = []
        results = []
        for code in parse_utf8(text):
            if state.assignments.has_key(code):
                n = state.assignments[code]
            else:
                if state.frozen:
                    raise pdfdoc.PDFError, "Font %s is already frozen, cannot add new character U+%04X" % (self.fontName, code)
                n = state.nextCode
                state.nextCode = state.nextCode + 1
                state.assignments[code] = n
                if (n & 0xFF) == 0:
                    state.subsets.append([])
                state.subsets[n >> 8].append(code)
            if (n >> 8) != curSet:
                if cur:
                    results.append((curSet, string.join(map(chr, cur), "")))
                curSet = (n >> 8)
                cur = []
            cur.append(n & 0xFF)
        if cur:
            results.append((curSet, string.join(map(chr, cur), "")))
        return results

    def getSubsetInternalName(self, subset, doc):
        """Returns the name of a PDF Font object corresponding to a given
        subset of this dynamic font.  Use this function instead of
        PDFDocument.getInternalFontName."""
        try: state = self.state[doc]
        except KeyError: state = self.state[doc] = TTFont.State()
        if subset < 0 or subset >= len(state.subsets):
            raise IndexError, 'Subset %d does not exist in font %s' % (subset, self.fontName)
        if state.internalName is None:
            state.internalName = 'F%d' % (len(doc.fontMapping) + 1)
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
        except KeyError: state = self.state[doc] = TTFont.State()
        state.frozen = 1
        for n in range(len(state.subsets)):
            subset = state.subsets[n]
            internalName = self.getSubsetInternalName(n, doc)[1:]
            baseFontName = "SUBSET+%s+%d" % (self.face.name, n)

            pdfFont = pdfdoc.PDFTrueTypeFont()
            pdfFont.__Comment__ = 'Font %s subset %d' % (self.fontName, n)
            pdfFont.Name = internalName
            pdfFont.BaseFont = baseFontName

            pdfFont.FirstChar = 0
            pdfFont.LastChar = len(subset) - 1

            widths = map(self.face.getCharWidth, subset)
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
