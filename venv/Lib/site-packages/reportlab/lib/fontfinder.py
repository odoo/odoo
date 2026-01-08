#Copyright ReportLab Europe Ltd. 2000-2019
#see license.txt for license details
__version__='3.4.22'

#modification of users/robin/ttflist.py.
__doc__="""This provides some general-purpose tools for finding fonts.

The FontFinder object can search for font files.  It aims to build
a catalogue of fonts which our framework can work with.  It may be useful
if you are building GUIs or design-time interfaces and want to present users
with a choice of fonts.

There are 3 steps to using it
1. create FontFinder and set options and directories
2. search
3. query

>>> import fontfinder
>>> ff = fontfinder.FontFinder()
>>> ff.addDirectories([dir1, dir2, dir3])
>>> ff.search()
>>> ff.getFamilyNames()   #or whichever queries you want...

Because the disk search takes some time to find and parse hundreds of fonts,
it can use a cache to store a file with all fonts found. The cache file name

For each font found, it creates a structure with
- the short font name
- the long font name
- the principal file (.pfb for type 1 fonts), and the metrics file if appropriate
- the time modified (unix time stamp)
- a type code ('ttf')
- the family name
- bold and italic attributes

One common use is to display families in a dialog for end users;
then select regular, bold and italic variants of the font.  To get
the initial list, use getFamilyNames; these will be in alpha order.

>>> ff.getFamilyNames()
['Bitstream Vera Sans', 'Century Schoolbook L', 'Dingbats', 'LettErrorRobot',
'MS Gothic', 'MS Mincho', 'Nimbus Mono L', 'Nimbus Roman No9 L',
'Nimbus Sans L', 'Vera', 'Standard Symbols L',
'URW Bookman L', 'URW Chancery L', 'URW Gothic L', 'URW Palladio L']

One can then obtain a specific font as follows

>>> f = ff.getFont('Bitstream Vera Sans', bold=False, italic=True)
>>> f.fullName
'Bitstream Vera Sans'
>>> f.fileName
'C:\\code\\reportlab\\fonts\\Vera.ttf'
>>>

It can also produce an XML report of fonts found by family, for the benefit
of non-Python applications.

Future plans might include using this to auto-register fonts; and making it
update itself smartly on repeated instantiation.
"""
import sys, os, pickle
from hashlib import md5
from xml.sax.saxutils import quoteattr
from time import process_time as clock
from reportlab.lib.utils import asBytes, asNative as _asNative

def asNative(s):
    try:
        return _asNative(s)
    except:
        return _asNative(s,enc='latin-1')

EXTENSIONS = ['.ttf','.ttc','.otf','.pfb','.pfa']

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

class FontDescriptor:
    """This is a short descriptive record about a font.

    typeCode should be a file extension e.g. ['ttf','ttc','otf','pfb','pfa']
    """
    def __init__(self):
        self.name = None
        self.fullName = None
        self.familyName = None
        self.styleName = None
        self.isBold = False   #true if it's somehow bold
        self.isItalic = False #true if it's italic or oblique or somehow slanty
        self.isFixedPitch = False
        self.isSymbolic = False   #false for Dingbats, Symbols etc.

        self.typeCode = None   #normally the extension minus the dot
        self.fileName = None  #full path to where we found it.
        self.metricsFileName = None  #defined only for type='type1pc', or 'type1mac'

        self.timeModified = 0

    def __repr__(self):
        return "FontDescriptor(%s)" % self.name

    def getTag(self):
        "Return an XML tag representation"
        attrs = []
        for k, v in self.__dict__.items():
            if k not in ['timeModified']:
                if v:
                    attrs.append('%s=%s' % (k, quoteattr(str(v))))
        return '<font ' + ' '.join(attrs) + '/>'

from reportlab.lib.utils import rl_isdir, rl_isfile, rl_listdir, rl_getmtime
class FontFinder:
    def __init__(self, dirs=[], useCache=True, validate=False, recur=False, fsEncoding=None, verbose=0):
        self.useCache = useCache
        self.validate = validate
        if fsEncoding is None:
            fsEncoding = sys.getfilesystemencoding()
        self._fsEncoding = fsEncoding or 'utf8'

        self._dirs = set()
        self._recur = recur
        self.addDirectories(dirs)
        self._fonts = []

        self._skippedFiles = [] #list of filenames we did not handle
        self._badFiles = []  #list of filenames we rejected

        self._fontsByName = {}
        self._fontsByFamily = {}
        self._fontsByFamilyBoldItalic = {}   #indexed by bold, italic
        self.verbose = verbose

    def addDirectory(self, dirName, recur=None):
        #aesthetics - if there are 2 copies of a font, should the first or last
        #be picked up?  might need reversing
        if rl_isdir(dirName):
            self._dirs.add(dirName)
            if recur if recur is not None else self._recur:
                for r,D,F in os.walk(dirName):
                    for d in D:
                        self._dirs.add(os.path.join(r,d))

    def addDirectories(self, dirNames,recur=None):
        for dirName in dirNames:
            self.addDirectory(dirName,recur=recur)

    def getFamilyNames(self):
        "Returns a list of the distinct font families found"
        if not self._fontsByFamily:
            fonts = self._fonts
            for font in fonts:
                fam = font.familyName
                if fam is None: continue
                if fam in self._fontsByFamily:
                    self._fontsByFamily[fam].append(font)
                else:
                    self._fontsByFamily[fam] = [font]
        fsEncoding = self._fsEncoding
        names = list(asBytes(_,enc=fsEncoding) for _ in self._fontsByFamily.keys())
        names.sort()
        return names

    def getFontsInFamily(self, familyName):
        "Return list of all font objects with this family name"
        return self._fontsByFamily.get(familyName,[])

    def getFamilyXmlReport(self):
        """Reports on all families found as XML.
        """
        lines = []
        lines.append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
        lines.append("<font_families>")
        for dirName in self._dirs:
            lines.append("    <directory name=%s/>" % quoteattr(asNative(dirName)))
        for familyName in self.getFamilyNames():
            if familyName:  #skip null case
                lines.append('    <family name=%s>' % quoteattr(asNative(familyName)))
                for font in self.getFontsInFamily(familyName):
                    lines.append('        ' + font.getTag())
                lines.append('    </family>')
        lines.append("</font_families>")
        return '\n'.join(lines)

    def getFontsWithAttributes(self, **kwds):
        """This is a general lightweight search."""
        selected = []
        for font in self._fonts:
            OK = True
            for k, v in kwds.items():
                if getattr(font, k, None) != v:
                    OK = False
            if OK:
                selected.append(font)
        return selected

    def getFont(self, familyName, bold=False, italic=False):
        """Try to find a font matching the spec"""

        for font in self._fonts:
            if font.familyName == familyName:
                if font.isBold == bold:
                    if font.isItalic == italic:
                        return font

        raise KeyError("Cannot find font %s with bold=%s, italic=%s" % (familyName, bold, italic))

    def _getCacheFileName(self):
        """Base this on the directories...same set of directories
        should give same cache"""
        fsEncoding = self._fsEncoding
        hash = md5(b''.join(asBytes(_,enc=fsEncoding) for _ in sorted(self._dirs))).hexdigest()
        from reportlab.lib.utils import get_rl_tempfile
        fn = get_rl_tempfile('fonts_%s.dat' % hash)
        return fn

    def save(self, fileName):
        f = open(fileName, 'wb')
        pickle.dump(self, f)
        f.close()

    def load(self, fileName):
        f = open(fileName, 'rb')
        finder2 = pickle.load(f)
        f.close()
        self.__dict__.update(finder2.__dict__)

    def search(self):
        if self.verbose:
            started = clock()
        if not self._dirs:
            raise ValueError("Font search path is empty!  Please specify search directories using addDirectory or addDirectories")

        if self.useCache:
            cfn = self._getCacheFileName()
            if rl_isfile(cfn):
                try:
                    self.load(cfn)
                    if self.verbose>=3:
                        print("loaded cached file with %d fonts (%s)" % (len(self._fonts), cfn))
                    return
                except:
                    pass  #pickle load failed.  Ho hum, maybe it's an old pickle.  Better rebuild it.

        for dirName in self._dirs:
            try:
                fileNames = rl_listdir(dirName)
            except:
                continue
            for fileName in fileNames:
                root, ext = os.path.splitext(fileName)
                if ext.lower() in EXTENSIONS:
                    #it's a font
                    f = FontDescriptor()
                    f.fileName = fileName = os.path.normpath(os.path.join(dirName, fileName))
                    try:
                        f.timeModified = rl_getmtime(fileName)
                    except:
                        self._skippedFiles.append(fileName)
                        continue

                    ext = ext.lower()
                    if ext[0] == '.':
                        ext = ext[1:]
                    f.typeCode = ext  #strip the dot

                    #what to do depends on type.  We only accept .pfb if we
                    #have .afm to go with it, and don't handle .otf now.

                    if ext in ('otf', 'pfa'):
                        self._skippedFiles.append(fileName)

                    elif ext in ('ttf','ttc'):
                        #parsing should check it for us
                        from reportlab.pdfbase.ttfonts import TTFontFile, TTFError
                        try:
                            font = TTFontFile(fileName,validate=self.validate)
                        except TTFError:
                            self._badFiles.append(fileName)
                            continue
                        f.name = font.name
                        f.fullName = font.fullName
                        f.styleName = font.styleName
                        f.familyName = font.familyName
                        f.isBold = (FF_FORCEBOLD == FF_FORCEBOLD & font.flags)
                        f.isItalic = (FF_ITALIC == FF_ITALIC & font.flags)

                    elif ext == 'pfb':

                        # type 1; we need an AFM file or have to skip.
                        if rl_isfile(os.path.join(dirName, root + '.afm')):
                            f.metricsFileName = os.path.normpath(os.path.join(dirName, root + '.afm'))
                        elif rl_isfile(os.path.join(dirName, root + '.AFM')):
                            f.metricsFileName = os.path.normpath(os.path.join(dirName, root + '.AFM'))
                        else:
                            self._skippedFiles.append(fileName)
                            continue
                        from reportlab.pdfbase.pdfmetrics import parseAFMFile

                        (info, glyphs) = parseAFMFile(f.metricsFileName)
                        f.name = info['FontName']
                        f.fullName = info.get('FullName', f.name)
                        f.familyName = info.get('FamilyName', None)
                        f.isItalic = (float(info.get('ItalicAngle', 0)) > 0.0)
                        #if the weight has the word bold, deem it bold
                        f.isBold = ('bold' in info.get('Weight','').lower())

                    self._fonts.append(f)
        if self.useCache:
            self.save(cfn)

        if self.verbose:
            finished = clock()
            print("found %d fonts; skipped %d; bad %d.  Took %0.2f seconds" % (
                len(self._fonts), len(self._skippedFiles), len(self._badFiles),
                finished - started
                ))

def test():
    #windows-centric test maybe
    from reportlab import rl_config
    ff = FontFinder(verbose=rl_config.verbose)
    ff.useCache = True
    ff.validate = True

    import reportlab
    ff.addDirectory('C:\\windows\\fonts')
    rlFontDir = os.path.join(os.path.dirname(reportlab.__file__), 'fonts')
    ff.addDirectory(rlFontDir)
    ff.search()

    print('cache file name...')
    print(ff._getCacheFileName())

    print('families...')
    for familyName in ff.getFamilyNames():
        print('\t%s' % familyName)

    print()
    outw = sys.stdout.write
    outw('fonts called Vera:')
    for font in ff.getFontsInFamily('Bitstream Vera Sans'):
        outw(' %s' % font.name)
    print()
    outw('Bold fonts\n\t')
    for font in ff.getFontsWithAttributes(isBold=True, isItalic=False):
        outw(font.fullName+' ')
    print()
    print('family report')
    print(ff.getFamilyXmlReport())

if __name__=='__main__':
    test()
