#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/pdfbase/cidfonts.py
#$Header $
__version__='3.3.0'
__doc__="""CID (Asian multi-byte) font support.

This defines classes to represent CID fonts.  They know how to calculate
their own width and how to write themselves into PDF files."""

import os
import marshal
import time
try:
    from hashlib import md5
except ImportError:
    from md5 import md5

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase._cidfontdata import allowedTypeFaces, allowedEncodings, CIDFontInfo, \
     defaultUnicodeEncodings, widthsByUnichar
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfdoc
from reportlab.lib.rl_accel import escapePDF
from reportlab.rl_config import CMapSearchPath
from reportlab.lib.utils import isSeq, isBytes

#quick hackery for 2.0 release.  Now we always do unicode, and have built in
#the CMAP data, any code to load CMap files is not needed.
DISABLE_CMAP = True


def findCMapFile(name):
    "Returns full filename, or raises error"
    for dirname in CMapSearchPath:
        cmapfile = dirname + os.sep + name
        if os.path.isfile(cmapfile):
            #print "found", cmapfile
            return cmapfile
    raise IOError('CMAP file for encodings "%s" not found!' % name)

def structToPDF(structure):
    "Converts deeply nested structure to PDFdoc dictionary/array objects"
    if isinstance(structure,dict):
        newDict = {}
        for k, v in structure.items():
            newDict[k] = structToPDF(v)
        return pdfdoc.PDFDictionary(newDict)
    elif isSeq(structure):
        newList = []
        for elem in structure:
            newList.append(structToPDF(elem))
        return pdfdoc.PDFArray(newList)
    else:
        return structure

class CIDEncoding(pdfmetrics.Encoding):
    """Multi-byte encoding.  These are loaded from CMAP files.

    A CMAP file is like a mini-codec.  It defines the correspondence
    between code points in the (multi-byte) input data and Character
    IDs. """
    # aims to do similar things to Brian Hooper's CMap class,
    # but I could not get it working and had to rewrite.
    # also, we should really rearrange our current encoding
    # into a SingleByteEncoding since many of its methods
    # should not apply here.

    def __init__(self, name, useCache=1):
        self.name = name
        self._mapFileHash = None
        self._codeSpaceRanges = []
        self._notDefRanges = []
        self._cmap = {}
        self.source = None
        if not DISABLE_CMAP:
            if useCache:
                from reportlab.lib.utils import get_rl_tempdir
                fontmapdir = get_rl_tempdir('FastCMAPS')
                if os.path.isfile(fontmapdir + os.sep + name + '.fastmap'):
                    self.fastLoad(fontmapdir)
                    self.source = fontmapdir + os.sep + name + '.fastmap'
                else:
                    self.parseCMAPFile(name)
                    self.source = 'CMAP: ' + name
                    self.fastSave(fontmapdir)
            else:
                self.parseCMAPFile(name)

    def _hash(self, text):
        hasher = md5()
        hasher.update(text)
        return hasher.digest()

    def parseCMAPFile(self, name):
        """This is a tricky one as CMAP files are Postscript
        ones.  Some refer to others with a 'usecmap'
        command"""
        #started = time.clock()
        cmapfile = findCMapFile(name)
        # this will CRAWL with the unicode encodings...
        rawdata = open(cmapfile, 'r').read()

        self._mapFileHash = self._hash(rawdata)
        #if it contains the token 'usecmap', parse the other
        #cmap file first....
        usecmap_pos = rawdata.find('usecmap')
        if  usecmap_pos > -1:
            #they tell us to look in another file
            #for the code space ranges. The one
            # to use will be the previous word.
            chunk = rawdata[0:usecmap_pos]
            words = chunk.split()
            otherCMAPName = words[-1]
            #print 'referred to another CMAP %s' % otherCMAPName
            self.parseCMAPFile(otherCMAPName)
            # now continue parsing this, as it may
            # override some settings


        words = rawdata.split()
        while words != []:
            if words[0] == 'begincodespacerange':
                words = words[1:]
                while words[0] != 'endcodespacerange':
                    strStart, strEnd, words = words[0], words[1], words[2:]
                    start = int(strStart[1:-1], 16)
                    end = int(strEnd[1:-1], 16)
                    self._codeSpaceRanges.append((start, end),)
            elif words[0] == 'beginnotdefrange':
                words = words[1:]
                while words[0] != 'endnotdefrange':
                    strStart, strEnd, strValue = words[0:3]
                    start = int(strStart[1:-1], 16)
                    end = int(strEnd[1:-1], 16)
                    value = int(strValue)
                    self._notDefRanges.append((start, end, value),)
                    words = words[3:]
            elif words[0] == 'begincidrange':
                words = words[1:]
                while words[0] != 'endcidrange':
                    strStart, strEnd, strValue = words[0:3]
                    start = int(strStart[1:-1], 16)
                    end = int(strEnd[1:-1], 16)
                    value = int(strValue)
                    # this means that 'start' corresponds to 'value',
                    # start+1 corresponds to value+1 and so on up
                    # to end
                    offset = 0
                    while start + offset <= end:
                        self._cmap[start + offset] = value + offset
                        offset = offset + 1
                    words = words[3:]

            else:
                words = words[1:]
        #finished = time.clock()
        #print 'parsed CMAP %s in %0.4f seconds' % (self.name, finished - started)

    def translate(self, text):
        "Convert a string into a list of CIDs"
        output = []
        cmap = self._cmap
        lastChar = ''
        for char in text:
            if lastChar != '':
                #print 'convert character pair "%s"' % (lastChar + char)
                num = ord(lastChar) * 256 + ord(char)
            else:
                #print 'convert character "%s"' % char
                num = ord(char)
            lastChar = char
            found = 0
            for low, high in self._codeSpaceRanges:
                if low < num < high:
                    try:
                        cid = cmap[num]
                        #print '%d -> %d' % (num, cid)
                    except KeyError:
                        #not defined.  Try to find the appropriate
                        # notdef character, or failing that return
                        # zero
                        cid = 0
                        for low2, high2, notdef in self._notDefRanges:
                            if low2 < num < high2:
                                cid = notdef
                                break
                    output.append(cid)
                    found = 1
                    break
            if found:
                lastChar = ''
            else:
                lastChar = char
        return output

    def fastSave(self, directory):
        f = open(os.path.join(directory, self.name + '.fastmap'), 'wb')
        marshal.dump(self._mapFileHash, f)
        marshal.dump(self._codeSpaceRanges, f)
        marshal.dump(self._notDefRanges, f)
        marshal.dump(self._cmap, f)
        f.close()

    def fastLoad(self, directory):
        started = time.clock()
        f = open(os.path.join(directory, self.name + '.fastmap'), 'rb')
        self._mapFileHash = marshal.load(f)
        self._codeSpaceRanges = marshal.load(f)
        self._notDefRanges = marshal.load(f)
        self._cmap = marshal.load(f)
        f.close()
        finished = time.clock()
        #print 'loaded %s in %0.4f seconds' % (self.name, finished - started)

    def getData(self):
        """Simple persistence helper.  Return a dict with all that matters."""
        return {
            'mapFileHash': self._mapFileHash,
            'codeSpaceRanges': self._codeSpaceRanges,
            'notDefRanges': self._notDefRanges,
            'cmap': self._cmap,
            }

class CIDTypeFace(pdfmetrics.TypeFace):
    """Multi-byte type face.

    Conceptually similar to a single byte typeface,
    but the glyphs are identified by a numeric Character
    ID (CID) and not a glyph name. """
    def __init__(self, name):
        """Initialised from one of the canned dictionaries in allowedEncodings

        Or rather, it will be shortly..."""
        pdfmetrics.TypeFace.__init__(self, name)
        self._extractDictInfo(name)
    def _extractDictInfo(self, name):
        try:
            fontDict = CIDFontInfo[name]
        except KeyError:
            raise KeyError("Unable to find information on CID typeface '%s'" % name +
                            "Only the following font names work:" + repr(allowedTypeFaces))
        descFont = fontDict['DescendantFonts'][0]
        self.ascent = descFont['FontDescriptor']['Ascent']
        self.descent = descFont['FontDescriptor']['Descent']
        self._defaultWidth = descFont['DW']
        self._explicitWidths = self._expandWidths(descFont['W'])

        # should really support self.glyphWidths, self.glyphNames
        # but not done yet.


    def _expandWidths(self, compactWidthArray):
        """Expands Adobe nested list structure to get a dictionary of widths.

        Here is an example of such a structure.::
        
            (
            # starting at character ID 1, next n  characters have the widths given.
            1,  (277,305,500,668,668,906,727,305,445,445,508,668,305,379,305,539),
            # all Characters from ID 17 to 26 are 668 em units wide
            17, 26, 668,
            27, (305, 305, 668, 668, 668, 566, 871, 727, 637, 652, 699, 574, 555,
                 676, 687, 242, 492, 664, 582, 789, 707, 734, 582, 734, 605, 605,
                 641, 668, 727, 945, 609, 609, 574, 445, 668, 445, 668, 668, 590,
                 555, 609, 547, 602, 574, 391, 609, 582, 234, 277, 539, 234, 895,
                 582, 605, 602, 602, 387, 508, 441, 582, 562, 781, 531, 570, 555,
                 449, 246, 449, 668),
            # these must be half width katakana and the like.
            231, 632, 500
            )
        
        """
        data = compactWidthArray[:]
        widths = {}
        while data:
            start, data = data[0], data[1:]
            if isSeq(data[0]):
                items, data = data[0], data[1:]
                for offset in range(len(items)):
                    widths[start + offset] = items[offset]
            else:
                end, width, data = data[0], data[1], data[2:]
                for idx in range(start, end+1):
                    widths[idx] = width
        return widths

    def getCharWidth(self, characterId):
        return self._explicitWidths.get(characterId, self._defaultWidth)

class CIDFont(pdfmetrics.Font):
    "Represents a built-in multi-byte font"
    _multiByte = 1

    def __init__(self, face, encoding):

        assert face in allowedTypeFaces, "TypeFace '%s' not supported! Use any of these instead: %s" % (face, allowedTypeFaces)
        self.faceName = face
        #should cache in registry...
        self.face = CIDTypeFace(face)

        assert encoding in allowedEncodings, "Encoding '%s' not supported!  Use any of these instead: %s" % (encoding, allowedEncodings)
        self.encodingName = encoding
        self.encoding = CIDEncoding(encoding)

        #legacy hack doing quick cut and paste.
        self.fontName = self.faceName + '-' + self.encodingName
        self.name = self.fontName

        # need to know if it is vertical or horizontal
        self.isVertical = (self.encodingName[-1] == 'V')

        #no substitutes initially
        self.substitutionFonts = []

    def formatForPdf(self, text):
        encoded = escapePDF(text)
        #print 'encoded CIDFont:', encoded
        return encoded

    def stringWidth(self, text, size, encoding=None):
        """This presumes non-Unicode input.  UnicodeCIDFont wraps it for that context"""
        cidlist = self.encoding.translate(text)
        if self.isVertical:
            #this part is "not checked!" but seems to work.
            #assume each is 1000 ems high
            return len(cidlist) * size
        else:
            w = 0
            for cid in cidlist:
                w = w + self.face.getCharWidth(cid)
            return 0.001 * w * size


    def addObjects(self, doc):
        """The explicit code in addMinchoObjects and addGothicObjects
        will be replaced by something that pulls the data from
        _cidfontdata.py in the next few days."""
        internalName = 'F' + repr(len(doc.fontMapping)+1)

        bigDict = CIDFontInfo[self.face.name]
        bigDict['Name'] = '/' + internalName
        bigDict['Encoding'] = '/' + self.encodingName

        #convert to PDF dictionary/array objects
        cidObj = structToPDF(bigDict)

        # link into document, and add to font map
        r = doc.Reference(cidObj, internalName)
        fontDict = doc.idToObject['BasicFonts'].dict
        fontDict[internalName] = r
        doc.fontMapping[self.name] = '/' + internalName


class UnicodeCIDFont(CIDFont):
    """Wraps up CIDFont to hide explicit encoding choice;
    encodes text for output as UTF16.

    lang should be one of 'jpn',chs','cht','kor' for now.
    if vertical is set, it will select a different widths array
    and possibly glyphs for some punctuation marks.

    halfWidth is only for Japanese.


    >>> dodgy = UnicodeCIDFont('nonexistent')
    Traceback (most recent call last):
    ...
    KeyError: "don't know anything about CID font nonexistent"
    >>> heisei = UnicodeCIDFont('HeiseiMin-W3')
    >>> heisei.name
    'HeiseiMin-W3'
    >>> heisei.language
    'jpn'
    >>> heisei.encoding.name
    'UniJIS-UCS2-H'
    >>> #This is how PDF data gets encoded.
    >>> print(heisei.formatForPdf('hello'))
    \\000h\\000e\\000l\\000l\\000o
    >>> tokyo = u'\u6771\u4AEC'
    >>> print(heisei.formatForPdf(tokyo))
    gqJ\\354
    >>> print(heisei.stringWidth(tokyo,10))
    20.0
    >>> print(heisei.stringWidth('hello world',10))
    45.83
    """

    def __init__(self, face, isVertical=False, isHalfWidth=False):
        #pass
        try:
            lang, defaultEncoding = defaultUnicodeEncodings[face]
        except KeyError:
            raise KeyError("don't know anything about CID font %s" % face)

        #we know the languages now.
        self.language = lang

        #rebuilt encoding string.  They follow rules which work
        #for the 7 fonts provided.
        enc = defaultEncoding[:-1]
        if isHalfWidth:
            enc = enc + 'HW-'
        if isVertical:
            enc = enc + 'V'
        else:
            enc = enc + 'H'

        #now we can do the more general case
        CIDFont.__init__(self, face, enc)
        #self.encName = 'utf_16_le'
        #it's simpler for unicode, just use the face name
        self.name = self.fontName = face
        self.vertical = isVertical
        self.isHalfWidth = isHalfWidth

        self.unicodeWidths = widthsByUnichar[self.name]


    def formatForPdf(self, text):
        #these ones should be encoded asUTF16 minus the BOM
        from codecs import utf_16_be_encode
        #print 'formatting %s: %s' % (type(text), repr(text))
        if isBytes(text):
            text = text.decode('utf8')
        utfText = utf_16_be_encode(text)[0]
        encoded = escapePDF(utfText)
        #print '  encoded:',encoded
        return encoded
        #
        #result = escapePDF(encoded)
        #print '    -> %s' % repr(result)
        #return result


    def stringWidth(self, text, size, encoding=None):
        "Just ensure we do width test on characters, not bytes..."
        if isBytes(text):
            text = text.decode('utf8')

        widths = self.unicodeWidths
        return size * 0.001 * sum([widths.get(uch, 1000) for uch in text])
        #return CIDFont.stringWidth(self, text, size, encoding)


def precalculate(cmapdir):
    # crunches through all, making 'fastmap' files
    import os
    files = os.listdir(cmapdir)
    for file in files:
        if os.path.isfile(cmapdir + os.sep + file + '.fastmap'):
            continue
        try:
            enc = CIDEncoding(file)
        except:
            print('cannot parse %s, skipping' % enc)
            continue
        enc.fastSave(cmapdir)
        print('saved %s.fastmap' % file)

def test():
    # only works if you have cirrect encodings on your box!
    c = Canvas('test_japanese.pdf')
    c.setFont('Helvetica', 30)
    c.drawString(100,700, 'Japanese Font Support')

    pdfmetrics.registerFont(CIDFont('HeiseiMin-W3','90ms-RKSJ-H'))
    pdfmetrics.registerFont(CIDFont('HeiseiKakuGo-W5','90ms-RKSJ-H'))


    # the two typefaces
    c.setFont('HeiseiMin-W3-90ms-RKSJ-H', 16)
    # this says "This is HeiseiMincho" in shift-JIS.  Not all our readers
    # have a Japanese PC, so I escaped it. On a Japanese-capable
    # system, print the string to see Kanji
    message1 = '\202\261\202\352\202\315\225\275\220\254\226\276\222\251\202\305\202\267\201B'
    c.drawString(100, 675, message1)
    c.save()
    print('saved test_japanese.pdf')


##    print 'CMAP_DIR = ', CMAP_DIR
##    tf1 = CIDTypeFace('HeiseiMin-W3')
##    print 'ascent = ',tf1.ascent
##    print 'descent = ',tf1.descent
##    for cid in [1,2,3,4,5,18,19,28,231,1742]:
##        print 'width of cid %d = %d' % (cid, tf1.getCharWidth(cid))

    encName = '90ms-RKSJ-H'
    enc = CIDEncoding(encName)
    print(message1, '->', enc.translate(message1))

    f = CIDFont('HeiseiMin-W3','90ms-RKSJ-H')
    print('width = %0.2f' % f.stringWidth(message1, 10))


    #testing all encodings
##    import time
##    started = time.time()
##    import glob
##    for encName in _cidfontdata.allowedEncodings:
##    #encName = '90ms-RKSJ-H'
##        enc = CIDEncoding(encName)
##        print 'encoding %s:' % encName
##        print '    codeSpaceRanges = %s' % enc._codeSpaceRanges
##        print '    notDefRanges = %s' % enc._notDefRanges
##        print '    mapping size = %d' % len(enc._cmap)
##    finished = time.time()
##    print 'constructed all encodings in %0.2f seconds' % (finished - started)

if __name__=='__main__':
    import doctest
    from reportlab.pdfbase import cidfonts
    doctest.testmod(cidfonts)
    #test()




