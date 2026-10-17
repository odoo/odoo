#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/pdfbase/pdfutils.py
__version__='3.3.0'
__doc__=''
# pdfutils.py - everything to do with images, streams,
# compression, and some constants

import os
import binascii
from io import BytesIO

from reportlab import rl_config
from reportlab.lib.utils import ImageReader, isUnicode
from reportlab.lib.rl_accel import asciiBase85Encode, asciiBase85Decode

def _chunker(src,dst=[],chunkSize=60):
    for i in range(0,len(src),chunkSize):
        dst.append(src[i:i+chunkSize])
    return dst

##########################################################
#
#  Image compression helpers.  Preprocessing a directory
#  of images will offer a vast speedup.
#
##########################################################
_mode2cs = {'RGB':'RGB', 'CMYK': 'CMYK', 'L': 'G'}
_mode2bpp = {'RGB': 3, 'CMYK':4, 'L':1}
def makeA85Image(filename,IMG=None, detectJpeg=False):
    import zlib
    img = ImageReader(filename)
    if IMG is not None:
        IMG.append(img)
        if detectJpeg and img.jpeg_fh():
            return None

    imgwidth, imgheight = img.getSize()
    raw = img.getRGBData()

    code = []
    append = code.append
    # this describes what is in the image itself
    append('BI')
    append('/W %s /H %s /BPC 8 /CS /%s /F [/A85 /Fl]' % (imgwidth, imgheight,_mode2cs[img.mode]))
    append('ID')
    #use a flate filter and Ascii Base 85
    assert len(raw) == imgwidth * imgheight*_mode2bpp[img.mode], "Wrong amount of data for image"
    compressed = zlib.compress(raw)   #this bit is very fast...
    encoded = asciiBase85Encode(compressed) #...sadly this may not be

    #append in blocks of 60 characters
    _chunker(encoded,code)

    append('EI')
    return code
def makeRawImage(filename,IMG=None,detectJpeg=False):
    import zlib
    img = ImageReader(filename)
    if IMG is not None:
        IMG.append(img)
        if detectJpeg and img.jpeg_fh():
            return None

    imgwidth, imgheight = img.getSize()
    raw = img.getRGBData()

    code = []
    append = code.append
    # this describes what is in the image itself
    append('BI')
    append('/W %s /H %s /BPC 8 /CS /%s /F [/Fl]' % (imgwidth, imgheight,_mode2cs[img.mode]))
    append('ID')
    #use a flate filter
    assert len(raw) == imgwidth * imgheight*_mode2bpp[img.mode], "Wrong amount of data for image"
    compressed = zlib.compress(raw)   #this bit is very fast...

    #append in blocks of 60 characters
    _chunker(compressed,code)

    append('EI')
    return code

def cacheImageFile(filename, returnInMemory=0, IMG=None):
    "Processes image as if for encoding, saves to a file with .a85 extension."

    cachedname = os.path.splitext(filename)[0] + (rl_config.useA85 and '.a85' or '.bin')
    if filename==cachedname:
        if cachedImageExists(filename):
            from reportlab.lib.utils import open_for_read
            if returnInMemory: return filter(None,open_for_read(cachedname).read().split('\r\n'))
        else:
            raise IOError('No such cached image %s' % filename)
    else:
        if rl_config.useA85:
            code = makeA85Image(filename,IMG)
        else:
            code = makeRawImage(filename,IMG)
        if returnInMemory: return code

        #save it to a file
        f = open(cachedname,'wb')
        f.write('\r\n'.join(code)+'\r\n')
        f.close()
        if rl_config.verbose:
            print('cached image as %s' % cachedname)


def preProcessImages(spec):
    """Preprocesses one or more image files.

    Accepts either a filespec ('C:\\mydir\\*.jpg') or a list
    of image filenames, crunches them all to save time.  Run this
    to save huge amounts of time when repeatedly building image
    documents."""

    import glob

    if isinstance(spec,str):
        filelist = glob.glob(spec)
    else:  #list or tuple OK
        filelist = spec

    for filename in filelist:
        if cachedImageExists(filename):
            if rl_config.verbose:
                print('cached version of %s already exists' % filename)
        else:
            cacheImageFile(filename)


def cachedImageExists(filename):
    """Determines if a cached image already exists for a given file.

    Determines if a cached image exists which has the same name
    and equal or newer date to the given file."""
    cachedname = os.path.splitext(filename)[0] + (rl_config.useA85 and '.a85' or 'bin')
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

def _normalizeLineEnds(text,desired='\r\n',unlikely='\x00\x01\x02\x03'):
    """Normalizes different line end character(s).

    Ensures all instances of CR, LF and CRLF end up as
    the specified one."""
    
    return (text
            .replace('\r\n', unlikely)
            .replace('\r', unlikely)
            .replace('\n', unlikely)
            .replace(unlikely, desired))

def _AsciiHexEncode(input):
    """Encodes input using ASCII-Hex coding.

    This is a verbose encoding used for binary data within
    a PDF file.  One byte binary becomes two bytes of ASCII.
    Helper function used by images."""
    if isUnicode(input):
        input = input.encode('utf-8')
    output = BytesIO()
    output.write(binascii.b2a_hex(input))
    output.write(b'>')
    return output.getvalue()


def _AsciiHexDecode(input):
    """Decodes input using ASCII-Hex coding.

    Not used except to provide a test of the inverse function."""

    #strip out all whitespace
    if not isUnicode(input):
        input = input.decode('utf-8')
    stripped = ''.join(input.split())
    assert stripped[-1] == '>', 'Invalid terminator for Ascii Hex Stream'
    stripped = stripped[:-1]  #chop off terminator
    assert len(stripped) % 2 == 0, 'Ascii Hex stream has odd number of bytes'

    return ''.join([chr(int(stripped[i:i+2],16)) for i in range(0,len(stripped),2)])
        
def _wrap(input, columns=60):
    "Wraps input at a given column size by inserting \r\n characters."
    output = []
    length = len(input)
    i = 0
    pos = columns * i
    while pos < length:
        output.append(input[pos:pos+columns])
        i = i + 1
        pos = columns * i
    #avoid HP printer problem
    if len(output[-1])==1:
        output[-2:] = [output[-2][:-1],output[-2][-1]+output[-1]]
    return '\r\n'.join(output)


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
    from reportlab.pdfbase.pdfdoc import PDFError

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
    dpi = (72,72)
    done = 0
    while not done:
        x = struct.unpack('B', image.read(1))
        if x[0] == 0xFF:                    #found marker
            x = struct.unpack('B', image.read(1))
            #print('marker=%2x' % x[0])
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
                return width, height, color, dpi
            elif x[0]==0xE0:
                x = struct.unpack('BB', image.read(2))
                n = (x[0] << 8) + x[1] - 2
                x = image.read(n)
                y = struct.unpack('BB', x[10:12])
                x = struct.unpack('BB', x[8:10])
                dpi = ((x[0]<<8) + x[1],(y[0]<<8)+y[1])
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
        return self.__rotate(asciiBase85Encode(''.join(map(chr,self.__fusc(list(map(ord,s)))))),self._n)

    def decrypt(self,s):
        return ''.join(map(chr,self.__fusc(list(map(ord,asciiBase85Decode(self.__rotate(s,-self._n)))))))

    def __rotate(self,s,n):
        l = len(s)
        if n<0: n = l+n
        n %= l
        if not n: return s
        return s[-n:]+s[:l-n]

    def __fusc(self,s):
        slen = len(s)
        return list(map(lambda x,y: x ^ y,s,list(map(ord,((int(slen/self._klen)+1)*self._k)[:slen]))))
