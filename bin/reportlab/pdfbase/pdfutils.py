#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/pdfbase/pdfutils.py
__version__=''' $Id: pdfutils.py 2765 2006-02-02 18:48:12Z rgbecker $ '''
__doc__=''
# pdfutils.py - everything to do with images, streams,
# compression, and some constants

import os
from reportlab import rl_config
from string import join, replace, strip, split
from reportlab.lib.utils import getStringIO, ImageReader

LINEEND = '\015\012'

def _chunker(src,dst=[],chunkSize=60):
    for i in xrange(0,len(src),chunkSize):
        dst.append(src[i:i+chunkSize])
    return dst

##########################################################
#
#  Image compression helpers.  Preprocessing a directory
#  of images will offer a vast speedup.
#
##########################################################

_mode2cs = {'RGB':'RGB', 'CMYK': 'CMYK', 'L': 'G'}

def makeA85Image(filename,IMG=None):
    import zlib
    img = ImageReader(filename)
    if IMG is not None: IMG.append(img)

    imgwidth, imgheight = img.getSize()
    raw = img.getRGBData()

    code = []
    append = code.append
    # this describes what is in the image itself
    append('BI')
    append('/W %s /H %s /BPC 8 /CS /%s /F [/A85 /Fl]' % (imgwidth, imgheight,_mode2cs[img.mode]))
    append('ID')
    #use a flate filter and Ascii Base 85
    assert(len(raw) == imgwidth * imgheight, "Wrong amount of data for image")
    compressed = zlib.compress(raw)   #this bit is very fast...
    encoded = _AsciiBase85Encode(compressed) #...sadly this may not be

    #append in blocks of 60 characters
    _chunker(encoded,code)

    append('EI')
    return code

def cacheImageFile(filename, returnInMemory=0, IMG=None):
    "Processes image as if for encoding, saves to a file with .a85 extension."

    cachedname = os.path.splitext(filename)[0] + '.a85'
    if filename==cachedname:
        if cachedImageExists(filename):
            from reportlab.lib.utils import open_for_read
            if returnInMemory: return split(open_for_read(cachedname).read(),LINEEND)[:-1]
        else:
            raise IOError, 'No such cached image %s' % filename
    else:
        code = makeA85Image(filename,IMG)
        if returnInMemory: return code

        #save it to a file
        f = open(cachedname,'wb')
        f.write(join(code, LINEEND)+LINEEND)
        f.close()
        if rl_config.verbose:
            print 'cached image as %s' % cachedname


def preProcessImages(spec):
    """Preprocesses one or more image files.

    Accepts either a filespec ('C:\mydir\*.jpg') or a list
    of image filenames, crunches them all to save time.  Run this
    to save huge amounts of time when repeatedly building image
    documents."""

    import types, glob

    if type(spec) is types.StringType:
        filelist = glob.glob(spec)
    else:  #list or tuple OK
        filelist = spec

    for filename in filelist:
        if cachedImageExists(filename):
            if rl_config.verbose:
                print 'cached version of %s already exists' % filename
        else:
            cacheImageFile(filename)


def cachedImageExists(filename):
    """Determines if a cached image already exists for a given file.

    Determines if a cached image exists which has the same name
    and equal or newer date to the given file."""
    cachedname = os.path.splitext(filename)[0] + '.a85'
    if os.path.isfile(cachedname):
        #see if it is newer
        original_date = os.stat(filename)[8]
        cached_date = os.stat(cachedname)[8]
        if original_date > cached_date:
            return 0
        else:
            return 1
    else:
        return 0


##############################################################
#
#            PDF Helper functions
#
##############################################################

try:
    from _rl_accel import escapePDF, _instanceEscapePDF
    _escape = escapePDF
except ImportError:
    try:
        from reportlab.lib._rl_accel import escapePDF, _instanceEscapePDF
        _escape = escapePDF
    except ImportError:
        _instanceEscapePDF=None
        if rl_config.sys_version>='2.1':
            _ESCAPEDICT={}
            for c in range(0,256):
                if c<32 or c>=127:
                    _ESCAPEDICT[chr(c)]= '\\%03o' % c
                elif c in (ord('\\'),ord('('),ord(')')):
                    _ESCAPEDICT[chr(c)] = '\\'+chr(c)
                else:
                    _ESCAPEDICT[chr(c)] = chr(c)
            del c
            #Michael Hudson donated this
            def _escape(s):
                return join(map(lambda c, d=_ESCAPEDICT: d[c],s),'')
        else:
            def _escape(s):
                """Escapes some PDF symbols (in fact, parenthesis).
                PDF escapes are almost like Python ones, but brackets
                need slashes before them too. Uses Python's repr function
                and chops off the quotes first."""
                s = repr(s)[1:-1]
                s = replace(s, '(','\(')
                s = replace(s, ')','\)')
                return s

def _normalizeLineEnds(text,desired=LINEEND):
    """Normalizes different line end character(s).

    Ensures all instances of CR, LF and CRLF end up as
    the specified one."""
    unlikely = '\000\001\002\003'
    text = replace(text, '\015\012', unlikely)
    text = replace(text, '\015', unlikely)
    text = replace(text, '\012', unlikely)
    text = replace(text, unlikely, desired)
    return text


def _AsciiHexEncode(input):
    """Encodes input using ASCII-Hex coding.

    This is a verbose encoding used for binary data within
    a PDF file.  One byte binary becomes two bytes of ASCII.
    Helper function used by images."""
    output = getStringIO()
    for char in input:
        output.write('%02x' % ord(char))
    output.write('>')
    return output.getvalue()


def _AsciiHexDecode(input):
    """Decodes input using ASCII-Hex coding.

    Not used except to provide a test of the inverse function."""

    #strip out all whitespace
    stripped = join(split(input),'')
    assert stripped[-1] == '>', 'Invalid terminator for Ascii Hex Stream'
    stripped = stripped[:-1]  #chop off terminator
    assert len(stripped) % 2 == 0, 'Ascii Hex stream has odd number of bytes'

    i = 0
    output = getStringIO()
    while i < len(stripped):
        twobytes = stripped[i:i+2]
        output.write(chr(eval('0x'+twobytes)))
        i = i + 2
    return output.getvalue()


if 1: # for testing always define this
    def _AsciiBase85EncodePYTHON(input):
        """Encodes input using ASCII-Base85 coding.

        This is a compact encoding used for binary data within
        a PDF file.  Four bytes of binary data become five bytes of
        ASCII.  This is the default method used for encoding images."""
        outstream = getStringIO()
        # special rules apply if not a multiple of four bytes.
        whole_word_count, remainder_size = divmod(len(input), 4)
        cut = 4 * whole_word_count
        body, lastbit = input[0:cut], input[cut:]

        for i in range(whole_word_count):
            offset = i*4
            b1 = ord(body[offset])
            b2 = ord(body[offset+1])
            b3 = ord(body[offset+2])
            b4 = ord(body[offset+3])

            if b1<128:
                num = (((((b1<<8)|b2)<<8)|b3)<<8)|b4
            else:
                num = 16777216L * b1 + 65536 * b2 + 256 * b3 + b4

            if num == 0:
                #special case
                outstream.write('z')
            else:
                #solve for five base-85 numbers
                temp, c5 = divmod(num, 85)
                temp, c4 = divmod(temp, 85)
                temp, c3 = divmod(temp, 85)
                c1, c2 = divmod(temp, 85)
                assert ((85**4) * c1) + ((85**3) * c2) + ((85**2) * c3) + (85*c4) + c5 == num, 'dodgy code!'
                outstream.write(chr(c1+33))
                outstream.write(chr(c2+33))
                outstream.write(chr(c3+33))
                outstream.write(chr(c4+33))
                outstream.write(chr(c5+33))

        # now we do the final bit at the end.  I repeated this separately as
        # the loop above is the time-critical part of a script, whereas this
        # happens only once at the end.

        #encode however many bytes we have as usual
        if remainder_size > 0:
            while len(lastbit) < 4:
                lastbit = lastbit + '\000'
            b1 = ord(lastbit[0])
            b2 = ord(lastbit[1])
            b3 = ord(lastbit[2])
            b4 = ord(lastbit[3])

            num = 16777216L * b1 + 65536 * b2 + 256 * b3 + b4

            #solve for c1..c5
            temp, c5 = divmod(num, 85)
            temp, c4 = divmod(temp, 85)
            temp, c3 = divmod(temp, 85)
            c1, c2 = divmod(temp, 85)

            #print 'encoding: %d %d %d %d -> %d -> %d %d %d %d %d' % (
            #    b1,b2,b3,b4,num,c1,c2,c3,c4,c5)
            lastword = chr(c1+33) + chr(c2+33) + chr(c3+33) + chr(c4+33) + chr(c5+33)
            #write out most of the bytes.
            outstream.write(lastword[0:remainder_size + 1])

        #terminator code for ascii 85
        outstream.write('~>')
        return outstream.getvalue()

    def _AsciiBase85DecodePYTHON(input):
        """Decodes input using ASCII-Base85 coding.

        This is not used - Acrobat Reader decodes for you
        - but a round trip is essential for testing."""
        outstream = getStringIO()
        #strip all whitespace
        stripped = join(split(input),'')
        #check end
        assert stripped[-2:] == '~>', 'Invalid terminator for Ascii Base 85 Stream'
        stripped = stripped[:-2]  #chop off terminator

        #may have 'z' in it which complicates matters - expand them
        stripped = replace(stripped,'z','!!!!!')
        # special rules apply if not a multiple of five bytes.
        whole_word_count, remainder_size = divmod(len(stripped), 5)
        #print '%d words, %d leftover' % (whole_word_count, remainder_size)
        #assert remainder_size <> 1, 'invalid Ascii 85 stream!'
        cut = 5 * whole_word_count
        body, lastbit = stripped[0:cut], stripped[cut:]

        for i in range(whole_word_count):
            offset = i*5
            c1 = ord(body[offset]) - 33
            c2 = ord(body[offset+1]) - 33
            c3 = ord(body[offset+2]) - 33
            c4 = ord(body[offset+3]) - 33
            c5 = ord(body[offset+4]) - 33

            num = ((85L**4) * c1) + ((85**3) * c2) + ((85**2) * c3) + (85*c4) + c5

            temp, b4 = divmod(num,256)
            temp, b3 = divmod(temp,256)
            b1, b2 = divmod(temp, 256)

            assert  num == 16777216 * b1 + 65536 * b2 + 256 * b3 + b4, 'dodgy code!'
            outstream.write(chr(b1))
            outstream.write(chr(b2))
            outstream.write(chr(b3))
            outstream.write(chr(b4))

        #decode however many bytes we have as usual
        if remainder_size > 0:
            while len(lastbit) < 5:
                lastbit = lastbit + '!'
            c1 = ord(lastbit[0]) - 33
            c2 = ord(lastbit[1]) - 33
            c3 = ord(lastbit[2]) - 33
            c4 = ord(lastbit[3]) - 33
            c5 = ord(lastbit[4]) - 33
            num = (((85*c1+c2)*85+c3)*85+c4)*85L + (c5
                     +(0,0,0xFFFFFF,0xFFFF,0xFF)[remainder_size])
            temp, b4 = divmod(num,256)
            temp, b3 = divmod(temp,256)
            b1, b2 = divmod(temp, 256)
            assert  num == 16777216 * b1 + 65536 * b2 + 256 * b3 + b4, 'dodgy code!'
            #print 'decoding: %d %d %d %d %d -> %d -> %d %d %d %d' % (
            #    c1,c2,c3,c4,c5,num,b1,b2,b3,b4)

            #the last character needs 1 adding; the encoding loses
            #data by rounding the number to x bytes, and when
            #divided repeatedly we get one less
            if remainder_size == 2:
                lastword = chr(b1)
            elif remainder_size == 3:
                lastword = chr(b1) + chr(b2)
            elif remainder_size == 4:
                lastword = chr(b1) + chr(b2) + chr(b3)
            else:
                lastword = ''
            outstream.write(lastword)

        #terminator code for ascii 85
        return outstream.getvalue()

try:
    from _rl_accel import _AsciiBase85Encode                    # builtin or on the path
except ImportError:
    try:
        from reportlab.lib._rl_accel import _AsciiBase85Encode  # where we think it should be
    except ImportError:
        _AsciiBase85Encode = _AsciiBase85EncodePYTHON

try:
    from _rl_accel import _AsciiBase85Decode                    # builtin or on the path
except ImportError:
    try:
        from reportlab.lib._rl_accel import _AsciiBase85Decode  # where we think it should be
    except ImportError:
        _AsciiBase85Decode = _AsciiBase85DecodePYTHON

def _wrap(input, columns=60):
    "Wraps input at a given column size by inserting LINEEND characters."

    output = []
    length = len(input)
    i = 0
    pos = columns * i
    while pos < length:
        output.append(input[pos:pos+columns])
        i = i + 1
        pos = columns * i

    return join(output, LINEEND)


#########################################################################
#
#  JPEG processing code - contributed by Eric Johnson
#
#########################################################################

# Read data from the JPEG file. We should probably be using PIL to
# get this information for us -- but this way is more fun!
# Returns (width, height, color components) as a triple
# This is based on Thomas Merz's code from GhostScript (viewjpeg.ps)
def readJPEGInfo(image):
    "Read width, height and number of components from open JPEG file."

    import struct
    from pdfdoc import PDFError

    #Acceptable JPEG Markers:
    #  SROF0=baseline, SOF1=extended sequential or SOF2=progressive
    validMarkers = [0xC0, 0xC1, 0xC2]

    #JPEG markers without additional parameters
    noParamMarkers = \
        [ 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0x01 ]

    #Unsupported JPEG Markers
    unsupportedMarkers = \
        [ 0xC3, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF ]

    #read JPEG marker segments until we find SOFn marker or EOF
    done = 0
    while not done:
        x = struct.unpack('B', image.read(1))
        if x[0] == 0xFF:                    #found marker
            x = struct.unpack('B', image.read(1))
            #print "Marker: ", '%0.2x' % x[0]
            #check marker type is acceptable and process it
            if x[0] in validMarkers:
                image.seek(2, 1)            #skip segment length
                x = struct.unpack('B', image.read(1)) #data precision
                if x[0] != 8:
                    raise PDFError('JPEG must have 8 bits per component')
                y = struct.unpack('BB', image.read(2))
                height = (y[0] << 8) + y[1]
                y = struct.unpack('BB', image.read(2))
                width =  (y[0] << 8) + y[1]
                y = struct.unpack('B', image.read(1))
                color =  y[0]
                return width, height, color
                done = 1
            elif x[0] in unsupportedMarkers:
                raise PDFError('JPEG Unsupported JPEG marker: %0.2x' % x[0])
            elif x[0] not in noParamMarkers:
                #skip segments with parameters
                #read length and skip the data
                x = struct.unpack('BB', image.read(2))
                image.seek( (x[0] << 8) + x[1] - 2, 1)

class _fusc:
    def __init__(self,k, n):
        assert k, 'Argument k should be a non empty string'
        self._k = k
        self._klen = len(k)
        self._n = int(n) or 7

    def encrypt(self,s):
        return self.__rotate(_AsciiBase85Encode(''.join(map(chr,self.__fusc(map(ord,s))))),self._n)

    def decrypt(self,s):
        return ''.join(map(chr,self.__fusc(map(ord,_AsciiBase85Decode(self.__rotate(s,-self._n))))))

    def __rotate(self,s,n):
        l = len(s)
        if n<0: n = l+n
        n %= l
        if not n: return s
        return s[-n:]+s[:l-n]

    def __fusc(self,s):
        slen = len(s)
        return map(lambda x,y: x ^ y,s,map(ord,((int(slen/self._klen)+1)*self._k)[:slen]))
