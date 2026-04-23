#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
'''default settings for reportlab

to override these drop a module rl_local_settings.py parallel to this file or
anywhere on the path.
'''
import os, sys
__version__='3.3.0'
__all__=tuple('''allowTableBoundsErrors
shapeChecking
defaultEncoding
defaultGraphicsFontName
pageCompression
useA85
defaultPageSize
defaultImageCaching
warnOnMissingFontGlyphs
verbose
showBoundary
emptyTableAction
invariant
eps_preview_transparent
eps_preview
eps_ttf_embed
eps_ttf_embed_uid
overlapAttachedSpace
longTableOptimize
autoConvertEncoding
_FUZZ
wrapA85
fsEncodings
odbc_driver
platypus_link_underline
canvas_basefontname
allowShortTableRows
imageReaderFlags
paraFontSizeHeightOffset
canvas_baseColor
ignoreContainerActions
ttfAsciiReadable
pdfMultiLine
pdfComments
debug
rtlSupport
listWrapOnFakeWidth
T1SearchPath
TTFSearchPath
CMapSearchPath
decimalSymbol
errorOnDuplicatePageLabelPage
autoGenerateMissingTTFName
allowTTFSubsetting
spaceShrinkage
underlineWidth
underlineOffset
underlineGap
strikeWidth
strikeOffset
strikeGap
hyphenationLang
uriWasteReduce
embeddedHyphenation
hyphenationMinWordLength
reserveTTFNotdef
documentLang
encryptionStrength
trustedHosts
trustedSchemes
renderPMBackend'''.split())

allowTableBoundsErrors =    1 # set to 0 to die on too large elements in tables in debug (recommend 1 for production use)
shapeChecking =             1
defaultEncoding =           'WinAnsiEncoding'       # 'WinAnsi' or 'MacRoman'
defaultGraphicsFontName=    'Times-Roman'           #initializer for STATE_DEFAULTS in shapes.py
pageCompression =           1                       # default page compression mode
useA85 =                    1                       #set to 0 to disable Ascii Base 85 stream filters
defaultPageSize =           'A4'                    #default page size
defaultImageCaching =       0                       #set to zero to remove those annoying cached images
warnOnMissingFontGlyphs =   0                       #if 1, warns of each missing glyph
verbose =                   0
showBoundary =              0                       # turns on and off boundary behaviour in Drawing
emptyTableAction=           'error'                 # one of 'error', 'indicate', 'ignore'
invariant=                  0                       #produces repeatable,identical PDFs with same timestamp info (for regression testing)
eps_preview_transparent=    None                    #set to white etc
eps_preview=                1                       #set to False to disable
eps_ttf_embed=              1                       #set to False to disable
eps_ttf_embed_uid=          0                       #set to 1 to enable
overlapAttachedSpace=       1                       #if set non false then adajacent flowable space after
                                                    #and space before are merged (max space is used).
longTableOptimize =         1                       #default do use Henning von Bargen's long table optimizations
autoConvertEncoding  =      0                       #convert internally as needed (experimental)
_FUZZ=                      1e-6                    #fuzz for layout arithmetic
wrapA85=                    0                       #set to 1 to get old wrapped line behaviour
fsEncodings=('utf8','cp1252','cp430')               #encodings to attempt utf8 conversion with
odbc_driver=                'odbc'                  #default odbc driver
platypus_link_underline=    0                       #paragraph links etc underlined if true
canvas_basefontname=        'Helvetica'             #this is used to initialize the canvas; if you override to make
                                                    #something else you are responsible for ensuring the font is registered etc etc
                                                    #this will be used everywhere and the font family connections will be made
                                                    #if the bold/italic/bold italic fonts are also registered and defined as a family.

allowShortTableRows=1                               #allows some rows in a table to be short
imageReaderFlags=0                                  #attempt to convert images into internal memory files to reduce
                                                    #the number of open files (see lib.utils.ImageReader)
                                                    #if imageReaderFlags&2 then attempt autoclosing of those files
                                                    #if imageReaderFlags&4 then cache data 
                                                    #if imageReaderFlags==-1 then use Ralf Schmitt's re-opening approach
paraFontSizeHeightOffset=   1                       #if true paragraphs start at height-fontSize
canvas_baseColor=           None                    #initialize the canvas fill and stroke colors if this is set
ignoreContainerActions=     1                       #if true then action flowables in flowable _Containers will be ignored
ttfAsciiReadable=           1                       #smaller subsets when set to 0
pdfMultiLine=               0                       #use more lines in pdf etc
pdfComments=                0                       #put in pdf comments
debug=                      0                       #for debugging code
rtlSupport=                 0                       #set to 1 to attempt import of RTL assistance eg fribidi etc etc
listWrapOnFakeWidth=        1                       #set to 0/False to force platypus.flowables._listWrapOn to report correct widths
                                                    #else it reports minimum(required,available) width

underlineWidth=             ''                      #empty to use canvas strokeWidth or a distance or number*<letter>
                                                    #   num * <letter> make value proportional to a font size
                                                    #   P paragraph font size
                                                    #   L line max font size
                                                    #   f first use font size
                                                    #   F max fontsize in the tag

underlineOffset=            '-0.125*F'              #fraction of fontSize from baseline to draw underlines at.
underlineGap=               '1'                     #gap for double/triple underline

strikeWidth=                ''
strikeOffset=               '0.25*F'                #fraction of fontSize from baseline to draw strike through at.
strikeGap=                  '1'                     #gap for double/triple strike

                                                    #by default typical value 0.05. may be overridden on a parastyle.
decimalSymbol=              '.'                     #what we use to align floats numerically
errorOnDuplicatePageLabelPage= 0                    #if True will cause repeated PageLabel page numbers to raise an error.
autoGenerateMissingTTFName=0                        #if true we try to auto generate any missing TTF font name

allowTTFSubsetting=         []                      #list of font file names that will be subsetted even when they
                                                    #have the no subsetting flag set. These should be fonts for which
                                                    #the user has explicit permission from the rights holder(s). 
                                                    #This flag could already be overcome by hacking the code.
                                                    #ReportLab takes no responsibility for the use of this setting.

spaceShrinkage=0.05                                 #allowable space shrinkage to make lines fit
hyphenationLang=''                                  #if pyphen installed set this to the language of your choice
                                                    #eg 'en_GB'

uriWasteReduce=0                                    #split URI if we would waste 0.3 of a line or if the URI#
                                                    #would not fit on the next line; if zero then no splitting
                                                    #is attempted. suggested value = 0.3
embeddedHyphenation=0                               #if true attempt hypenation of words with embedded hyphens
hyphenationMinWordLength=5                          #minimum length of words that can be hyphenated
reserveTTFNotdef=0                                  #if true force subset element 0 to be zero(.notdef)
                                                    #helps to fix bug in edge
documentLang=None                                   #pdf document catalog Lang value xx-xx not ee_xx
encryptionStrength=40                               #the bits for standard encryption 40, 128 or 256 (AES)
trustedHosts=None                                   #set to a list of trusted for access hosts None means
                                                    #all are trusted glob patterns eg *.reportlab.com are
                                                    #allowed. In environment use a comma separated string.
trustedSchemes=['file', 'rml', 'data', 'https',     #these url schemes are trusted
                'http', 'ftp']
renderPMBackend='_renderPM'                         #or 'rlPyCairo' if available

# places to look for T1Font information
T1SearchPath =  (
                'c:/Program Files/Adobe/Acrobat 9.0/Resource/Font', 
                'c:/Program Files/Adobe/Acrobat 8.0/Resource/Font', 
                'c:/Program Files/Adobe/Acrobat 7.0/Resource/Font', 
                'c:/Program Files/Adobe/Acrobat 6.0/Resource/Font', #Win32, Acrobat 6
                'c:/Program Files/Adobe/Acrobat 5.0/Resource/Font', #Win32, Acrobat 5
                'c:/Program Files/Adobe/Acrobat 4.0/Resource/Font', #Win32, Acrobat 4
                '%(disk)s/Applications/Python %(sys_version)s/reportlab/fonts', #Mac?
                '/usr/lib/Acrobat9/Resource/Font',      #Linux, Acrobat 5?
                '/usr/lib/Acrobat8/Resource/Font',      #Linux, Acrobat 5?
                '/usr/lib/Acrobat7/Resource/Font',      #Linux, Acrobat 5?
                '/usr/lib/Acrobat6/Resource/Font',      #Linux, Acrobat 5?
                '/usr/lib/Acrobat5/Resource/Font',      #Linux, Acrobat 5?
                '/usr/lib/Acrobat4/Resource/Font',      #Linux, Acrobat 4
                '/usr/local/Acrobat9/Resource/Font',    #Linux, Acrobat 5?
                '/usr/local/Acrobat8/Resource/Font',    #Linux, Acrobat 5?
                '/usr/local/Acrobat7/Resource/Font',    #Linux, Acrobat 5?
                '/usr/local/Acrobat6/Resource/Font',    #Linux, Acrobat 5?
                '/usr/local/Acrobat5/Resource/Font',    #Linux, Acrobat 5?
                '/usr/local/Acrobat4/Resource/Font',    #Linux, Acrobat 4
                '/usr/share/fonts/default/Type1',       #Linux, Fedora
                '%(REPORTLAB_DIR)s/fonts',              #special
                '%(REPORTLAB_DIR)s/../fonts',           #special
                '%(REPORTLAB_DIR)s/../../fonts',        #special
                '%(CWD)s/fonts',                        #special
                '~/fonts',
                '~/.fonts',
                '%(XDG_DATA_HOME)s/fonts',
                '~/.local/share/fonts',
                 )

# places to look for TT Font information
TTFSearchPath = (
                'c:/winnt/fonts',
                'c:/windows/fonts',
                '/usr/lib/X11/fonts/TrueType/',
                '/usr/share/fonts/truetype',
                '/usr/share/fonts',             #Linux, Fedora
                '/usr/share/fonts/dejavu',      #Linux, Fedora
                '%(REPORTLAB_DIR)s/fonts',      #special
                '%(REPORTLAB_DIR)s/../fonts',   #special
                '%(REPORTLAB_DIR)s/../../fonts',#special
                '%(CWD)s/fonts',                #special
                '~/fonts',
                '~/.fonts',
                '%(XDG_DATA_HOME)s/fonts',
                '~/.local/share/fonts',
                #mac os X - from
                #http://developer.apple.com/technotes/tn/tn2024.html
                '~/Library/Fonts',
                '/Library/Fonts',
                '/Network/Library/Fonts',
                '/System/Library/Fonts',
                )

# places to look for CMap files - should ideally merge with above
CMapSearchPath = (
                  '/usr/lib/Acrobat9/Resource/CMap',
                  '/usr/lib/Acrobat8/Resource/CMap',
                  '/usr/lib/Acrobat7/Resource/CMap',
                  '/usr/lib/Acrobat6/Resource/CMap',
                  '/usr/lib/Acrobat5/Resource/CMap',
                  '/usr/lib/Acrobat4/Resource/CMap',
                  '/usr/local/Acrobat9/Resource/CMap',
                  '/usr/local/Acrobat8/Resource/CMap',
                  '/usr/local/Acrobat7/Resource/CMap',
                  '/usr/local/Acrobat6/Resource/CMap',
                  '/usr/local/Acrobat5/Resource/CMap',
                  '/usr/local/Acrobat4/Resource/CMap',
                  'C:\\Program Files\\Adobe\\Acrobat\\Resource\\CMap',
                  'C:\\Program Files\\Adobe\\Acrobat 9.0\\Resource\\CMap',
                  'C:\\Program Files\\Adobe\\Acrobat 8.0\\Resource\\CMap',
                  'C:\\Program Files\\Adobe\\Acrobat 7.0\\Resource\\CMap',
                  'C:\\Program Files\\Adobe\\Acrobat 6.0\\Resource\\CMap',
                  'C:\\Program Files\\Adobe\\Acrobat 5.0\\Resource\\CMap',
                  'C:\\Program Files\\Adobe\\Acrobat 4.0\\Resource\\CMap',
                  '%(REPORTLAB_DIR)s/fonts/CMap',       #special
                  '%(REPORTLAB_DIR)s/../fonts/CMap',    #special
                  '%(REPORTLAB_DIR)s/../../fonts/CMap', #special
                  '%(CWD)s/fonts/CMap',             #special
                  '%(CWD)s/fonts',              #special
                  '~/fonts/CMap',
                  '~/.fonts/CMap',
                  '%(XDG_DATA_HOME)s/fonts/CMap',
                  '~/.local/share/fonts/CMap',
                  )

if sys.platform.startswith('linux'):
    def _findFontDirs(*ROOTS):
        R = [].append
        for rootd in ROOTS:
            for root, dirs, files in os.walk(rootd):
                if not files: continue
                R(root)
        return tuple(R.__self__)
    T1SearchPath = T1SearchPath + _findFontDirs(
                        '/usr/share/fonts/type1',
                        '/usr/share/fonts/Type1',
                        )
    TTFSearchPath = TTFSearchPath + _findFontDirs(
                        '/usr/share/fonts/truetype',
                        '/usr/share/fonts/TTF',
                        )
