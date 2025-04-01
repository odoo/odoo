#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/pdfbase/_cidfontdata.py
#$Header $
__version__='3.3.0'
__doc__="""
This defines additional static data to support CID fonts.

Canned data is provided for the Japanese fonts supported by Adobe. We
can add Chinese, Korean and Vietnamese in due course. The data was
extracted by creating very simple postscript documents and running
through Distiller, then examining the resulting PDFs.

Each font is described as a big nested dictionary.  This lets us keep
code out of the module altogether and avoid circular dependencies.

The encoding and font data are grouped by some standard 'language
prefixes'::

    chs = Chinese Simplified (mainland)
    cht = Chinese Traditional (Taiwan)
    kor = Korean
    jpn = Japanese
"""


languages = ['jpn', 'kor', 'cht', 'chs']

#breaking down the lists let us check if something is present
#for a specific language
typeFaces_chs = ['STSong-Light'] # to do
typeFaces_cht = ['MSung-Light']  #, 'MHei-Medium'] # to do
typeFaces_jpn = ['HeiseiMin-W3', 'HeiseiKakuGo-W5']
typeFaces_kor = ['HYSMyeongJo-Medium','HYGothic-Medium']

allowedTypeFaces = typeFaces_chs + typeFaces_cht + typeFaces_jpn + typeFaces_kor




encodings_jpn = [
    # official encoding names, comments taken verbatim from PDF Spec
    '83pv-RKSJ-H',      #Macintosh, JIS X 0208 character set with KanjiTalk6
                        #extensions, Shift-JIS encoding, Script Manager code 1
    '90ms-RKSJ-H',      #Microsoft Code Page 932 (lfCharSet 0x80), JIS X 0208
                        #character set with NEC and IBM extensions
    '90ms-RKSJ-V',      #Vertical version of 90ms-RKSJ-H
    '90msp-RKSJ-H',     #Same as 90ms-RKSJ-H, but replaces half-width Latin
                        #characters with proportional forms
    '90msp-RKSJ-V',     #Vertical version of 90msp-RKSJ-H
    '90pv-RKSJ-H',      #Macintosh, JIS X 0208 character set with KanjiTalk7
                        #extensions, Shift-JIS encoding, Script Manager code 1
    'Add-RKSJ-H',       #JIS X 0208 character set with Fujitsu FMR extensions,
                        #Shift-JIS encoding
    'Add-RKSJ-V',       #Vertical version of Add-RKSJ-H
    'EUC-H',            #JIS X 0208 character set, EUC-JP encoding
    'EUC-V',            #Vertical version of EUC-H
    'Ext-RKSJ-H',       #JIS C 6226 (JIS78) character set with NEC extensions,
                        #Shift-JIS encoding
    'Ext-RKSJ-V',       #Vertical version of Ext-RKSJ-H
    'H',                #JIS X 0208 character set, ISO-2022-JP encoding,
    'V',                #Vertical version of H
    'UniJIS-UCS2-H',    #Unicode (UCS-2) encoding for the Adobe-Japan1 character
                        #collection
    'UniJIS-UCS2-V',    #Vertical version of UniJIS-UCS2-H
    'UniJIS-UCS2-HW-H', #Same as UniJIS-UCS2-H, but replaces proportional Latin
                        #characters with half-width forms
    'UniJIS-UCS2-HW-V'  #Vertical version of UniJIS-UCS2-HW-H
    ]
encodings_kor = [
    'KSC-EUC-H',        # KS X 1001:1992 character set, EUC-KR encoding
    'KSC-EUC-V',        # Vertical version of KSC-EUC-H
    'KSCms-UHC-H',      # Microsoft Code Page 949 (lfCharSet 0x81), KS X 1001:1992
                        #character set plus 8,822 additional hangul, Unified Hangul
                        #Code (UHC) encoding
    'KSCms-UHC-V',      #Vertical version of KSCms-UHC-H
    'KSCms-UHC-HW-H',   #Same as KSCms-UHC-H, but replaces proportional Latin
                        # characters with halfwidth forms
    'KSCms-UHC-HW-V',   #Vertical version of KSCms-UHC-HW-H
    'KSCpc-EUC-H',      #Macintosh, KS X 1001:1992 character set with MacOS-KH
                        #extensions, Script Manager Code 3
    'UniKS-UCS2-H',     #Unicode (UCS-2) encoding for the Adobe-Korea1 character collection
    'UniKS-UCS2-V'      #Vertical version of UniKS-UCS2-H

    ]

encodings_chs = [

    'GB-EUC-H',         # Microsoft Code Page 936 (lfCharSet 0x86), GB 2312-80
                        # character set, EUC-CN encoding
    'GB-EUC-V',         # Vertical version of GB-EUC-H
    'GBpc-EUC-H',       # Macintosh, GB 2312-80 character set, EUC-CN encoding,
                        # Script Manager code 2
    'GBpc-EUC-V',       # Vertical version of GBpc-EUC-H
    'GBK-EUC-H',        # Microsoft Code Page 936 (lfCharSet 0x86), GBK character
                        # set, GBK encoding
    'GBK-EUC-V',        # Vertical version of GBK-EUC-V
    'UniGB-UCS2-H',     # Unicode (UCS-2) encoding for the Adobe-GB1
                        # character collection
    'UniGB-UCS2-V'     # Vertical version of UniGB-UCS2-H.
    ]

encodings_cht = [
    'B5pc-H',           # Macintosh, Big Five character set, Big Five encoding,
                        # Script Manager code 2
    'B5pc-V',           # Vertical version of B5pc-H
    'ETen-B5-H',        # Microsoft Code Page 950 (lfCharSet 0x88), Big Five
                        # character set with ETen extensions
    'ETen-B5-V',        # Vertical version of ETen-B5-H
    'ETenms-B5-H',      # Microsoft Code Page 950 (lfCharSet 0x88), Big Five
                        # character set with ETen extensions; this uses proportional
                        # forms for half-width Latin characters.
    'ETenms-B5-V',      # Vertical version of ETenms-B5-H
    'CNS-EUC-H',        # CNS 11643-1992 character set, EUC-TW encoding
    'CNS-EUC-V',        # Vertical version of CNS-EUC-H
    'UniCNS-UCS2-H',    # Unicode (UCS-2) encoding for the Adobe-CNS1
                        # character collection
    'UniCNS-UCS2-V'    # Vertical version of UniCNS-UCS2-H.
    ]

# the Identity encodings simply dump out all character
# in the font in the order they were defined.
allowedEncodings = (['Identity-H', 'Identity-V'] +
                    encodings_chs +
                    encodings_cht +
                    encodings_jpn +
                    encodings_kor
                    )

defaultUnicodeEncodings = {
    #we ddefine a default Unicode encoding for each face name;
    #this should be the most commonly used horizontal unicode encoding;
    #also define a 3-letter language code.
    'HeiseiMin-W3': ('jpn','UniJIS-UCS2-H'),
    'HeiseiKakuGo-W5': ('jpn','UniJIS-UCS2-H'),
    'STSong-Light': ('chs', 'UniGB-UCS2-H'),
    'MSung-Light': ('cht', 'UniGB-UCS2-H'),
    #'MHei-Medium': ('cht', 'UniGB-UCS2-H'),
    'HYSMyeongJo-Medium': ('kor', 'UniKS-UCS2-H'),
    'HYGothic-Medium': ('kor','UniKS-UCS2-H'),
    }

typeFaces_chs = ['STSong-Light'] # to do
typeFaces_cht = ['MSung-Light', 'MHei-Medium'] # to do
typeFaces_jpn = ['HeiseiMin-W3', 'HeiseiKakuGo-W5']
typeFaces_kor = ['HYSMyeongJo-Medium','HYGothic-Medium']


#declare separately those used for unicode
unicode_encodings = [enc for enc in allowedEncodings if 'UCS2' in enc]


CIDFontInfo = {}
#statically describe the fonts in Adobe's Japanese Language Packs
CIDFontInfo['HeiseiMin-W3'] = {
            'Type':'/Font',
            'Subtype':'/Type0',
            'Name': '/%(internalName)s' , #<-- the internal name
            'BaseFont': '/HeiseiMin-W3',
            'Encoding': '/%(encodings)s',

            #there could be several descendant fonts if it is an old-style
            #type 0 compound font.  For CID fonts there is just one.
            'DescendantFonts': [{
                'Type':'/Font',
                'Subtype':'/CIDFontType0',
                'BaseFont':'/HeiseiMin-W3',
                'FontDescriptor': {
                    'Type': '/FontDescriptor',
                    'Ascent': 723,
                    'CapHeight': 709,
                    'Descent': -241,
                    'Flags': 6,
                    'FontBBox': (-123, -257, 1001, 910),
                    'FontName': '/HeiseiMin-W3',
                    'ItalicAngle': 0,
                    'StemV': 69,
                    'XHeight': 450#,
#                    'Style': {'Panose': '<010502020400000000000000>'}
                    },
                'CIDSystemInfo': {
                    'Registry': '(Adobe)',
                    'Ordering': '(Japan1)',
                    'Supplement': 2
                    },
                #default width is 1000 em units
                'DW': 1000,
                #widths of any which are not the default.
                'W': [1, [250, 333, 408, 500],
                      5, [500, 833, 778, 180, 333],
                      10, [333, 500, 564, 250, 333, 250, 278, 500],
                      18, 26, 500, 27, 28, 278, 29, 31, 564,
                      32, [444, 921, 722, 667],
                      36, [667, 722, 611, 556, 722],
                      41, [722, 333, 389, 722, 611, 889, 722],
                      48, [722, 556, 722, 667, 556, 611, 722],
                      55, [722, 944, 722],
                      58, [722, 611, 333, 500, 333, 469, 500, 333,
                           444, 500, 444, 500, 444, 333, 500],
                      73, [500, 278],
                      75, [278, 500, 278, 778, 500], 80, 82, 500,
                      83, [333, 389, 278, 500],
                      87, [500, 722, 500],
                      90, [500, 444, 480, 200, 480, 333],
                      97, [278], 99, [200], 101, [333, 500], 103, [500, 167],
                      107, [500], 109, [500, 333], 111, [333, 556],
                      113, [556, 500], 117, [250], 119, [350, 333, 444],
                      123, [500], 126, [444, 333], 128, 137, 333,
                      138, [1000, 889, 276, 611, 722, 889, 310, 667, 278],
                      147, [278, 500, 722, 500, 564, 760, 564, 760],
                      157, 158, 300, 159, [500, 300, 750], 162, 163, 750,
                      164, 169, 722, 170, [667, 611], 172, 174, 611, 175,
                      178, 333, 179, 185, 722, 187, 191, 722, 192,
                      [556, 444], 194, 203, 444, 204, 207, 278, 208,
                      214, 500, 216, 222, 500,
                      223, [556, 722, 611, 500, 389, 980, 444],
                      231, [500], 323, [500], 325, [500],
                      327, 389, 500]
##                'W': (
##                    # starting at character ID 1, next n  characters have the widths given.
##                    1,  (277,305,500,668,668,906,727,305,445,445,508,668,305,379,305,539),
##                    # all Characters from ID 17 to 26 are 668 em units wide
##                    17, 26, 668,
##                    27, (305, 305, 668, 668, 668, 566, 871, 727, 637, 652, 699, 574, 555,
##                         676, 687, 242, 492, 664, 582, 789, 707, 734, 582, 734, 605, 605,
##                         641, 668, 727, 945, 609, 609, 574, 445, 668, 445, 668, 668, 590,
##                         555, 609, 547, 602, 574, 391, 609, 582, 234, 277, 539, 234, 895,
##                         582, 605, 602, 602, 387, 508, 441, 582, 562, 781, 531, 570, 555,
##                         449, 246, 449, 668),
##                    # these must be half width katakana and the like.
##                    231, 632, 500
##                    )
                }]# end list of descendant fonts
            } #end HeiseiMin-W3

CIDFontInfo['HeiseiKakuGo-W5'] =  {'Type':'/Font',
            'Subtype':'/Type0',
            'Name': '/%(internalName)s', #<-- the internal name
            'BaseFont': '/HeiseiKakuGo-W5',
            'Encoding': '/%(encodings)s',
            'DescendantFonts': [{'Type':'/Font',
                'Subtype':'/CIDFontType0',
                'BaseFont':'/HeiseiKakuGo-W5',
                'FontDescriptor': {
                    'Type': '/FontDescriptor',
                    'Ascent': 752,
                    'CapHeight': 737,
                    'Descent': -221,
                    'Flags': 4,
                    'FontBBox': [-92, -250, 1010, 922],
                    'FontName': '/HeiseKakuGo-W5',
                    'ItalicAngle': 0,
                    'StemH': 0,
                    'StemV': 114,
                    'XHeight': 553,
##                    'Style': {'Panose': '<0801020b0600000000000000>'}
                    },
                'CIDSystemInfo': {
                    'Registry': '(Adobe)',
                    'Ordering': '(Japan1)',
                    'Supplement': 2
                    },
                'DW': 1000,
                'W': (
                    1, (277,305,500,668,668,906,727,305,445,445,508,668,305,379,305,539),
                    17, 26, 668,
                    27, (305, 305, 668, 668, 668, 566, 871, 727, 637, 652, 699, 574, 555,
                                         676, 687, 242, 492, 664, 582, 789, 707, 734, 582, 734, 605, 605,
                                         641, 668, 727, 945, 609, 609, 574, 445, 668, 445, 668, 668, 590,
                                         555, 609, 547, 602, 574, 391, 609, 582, 234, 277, 539, 234, 895,
                                         582, 605, 602, 602, 387, 508, 441, 582, 562, 781, 531, 570, 555,
                                         449, 246, 449, 668),
                    231, 632, 500
                    )
                }] # end descendant fonts
            }

CIDFontInfo['HYGothic-Medium'] =  {'Type':'/Font',
            'Subtype':'/Type0',
            'Name': '/%(internalName)s', #<-- the internal name
            'BaseFont': '/' + 'HYGothic-Medium',
            'Encoding': '/%(encodings)s',
            'DescendantFonts': [{'Type':'/Font',
                'Subtype':'/CIDFontType0',
                'BaseFont':'/'+'HYGothic-Medium',
                'FontDescriptor': {
                    'Type': '/FontDescriptor',
                    'Ascent': 752,
                    'AvgWidth': -271,
                    'CapHeight': 737,
                    'Descent': -142,
                    'Flags': 6,
                    'FontBBox': [-6, -145, 1003, 880],
                    'FontName': '/'+'HYSMyeongJo-Medium',
                    'ItalicAngle': 0,
                    'Leading': 148,
                    'MaxWidth': 1000,
                    'MissingWidth': 500,
                    'StemH': 0,
                    'StemV': 58,
                    'XHeight': 553
                    },
                'CIDSystemInfo': {
                    'Registry': '(Adobe)',
                    'Ordering': '(Korea1)',
                    'Supplement': 1
                    },
                'DW': 1000,
                'W': (1, 94, 500)
                }] # end descendant fonts
            }

CIDFontInfo['HYSMyeongJo-Medium'] =  {'Type':'/Font',
            'Subtype':'/Type0',
            'Name': '/%(internalName)s', #<-- the internal name
            'BaseFont': '/' + 'HYSMyeongJo-Medium',
            'Encoding': '/%(encodings)s',
            'DescendantFonts': [{'Type':'/Font',
                'Subtype':'/CIDFontType2',
                'BaseFont':'/'+'HYSMyeongJo-Medium',
                'FontDescriptor': {
                    'Type': '/FontDescriptor',
                    'Ascent': 752,
                    'AvgWidth': 500,
                    'CapHeight': 737,
                    'Descent': -271,
                    'Flags': 6,
                    'FontBBox': [0, -148, 1001, 880],
                    'FontName': '/'+'HYSMyeongJo-Medium',
                    'ItalicAngle': 0,
                    'Leading': 148,
                    'MaxWidth': 1000,
                    'MissingWidth': 500,
                    'StemH': 91,
                    'StemV': 58,
                    'XHeight': 553
                    },
                'CIDSystemInfo': {
                    'Registry': '(Adobe)',
                    'Ordering': '(Korea1)',
                    'Supplement': 1
                    },
                'DW': 1000,
                'W': [1, [333, 416],
                      3, [416, 833, 625, 916, 833, 250, 500],
                      10, 11, 500,
                      12, [833, 291, 833, 291, 375, 625],
                      18, 26, 625, 27, 28, 333, 29, 30, 833,
                      31, [916, 500, 1000, 791, 708],
                      36, [708, 750, 708, 666, 750, 791, 375,
                           500, 791, 666, 916, 791, 750, 666,
                           750, 708, 666, 791],
                      54, [791, 750, 1000, 708],
                      58, [708, 666, 500, 375, 500],
                      63, 64, 500,
                      65, [333, 541, 583, 541, 583],
                      70, [583, 375, 583],
                      73, [583, 291, 333, 583, 291, 875, 583],
                      80, 82, 583,
                      83, [458, 541, 375, 583],
                      87, [583, 833, 625],
                      90, [625, 500, 583], 93, 94, 583,
                      95, [750]
                      ]
                }] # end descendant fonts
            }

#WARNING - not checked, just copied Korean to get some output

CIDFontInfo['STSong-Light'] =  {'Type':'/Font',
            'Subtype':'/Type0',
            'Name': '/%(internalName)s', #<-- the internal name
            'BaseFont': '/' + 'STSong-Light',
            'Encoding': '/%(encodings)s',
            'DescendantFonts': [{'Type':'/Font',
                'Subtype':'/CIDFontType0',
                'BaseFont':'/'+'STSong-Light',
                'FontDescriptor': {
                    'Type': '/FontDescriptor',
                    'Ascent': 752,
                    'CapHeight': 737,
                    'Descent': -271,
                    'Flags': 6,
                    'FontBBox': [-25, -254, 1000, 880],
                    'FontName': '/'+'STSongStd-Light',
                    'ItalicAngle': 0,
                    'Leading': 148,
                    'MaxWidth': 1000,
                    'MissingWidth': 500,
                    'StemH': 91,
                    'StemV': 58,
                    'XHeight': 553
                    },
                'CIDSystemInfo': {
                    'Registry': '(Adobe)',
                    'Ordering': '(GB1)',
                    'Supplement': 0
                    },
                'DW': 1000,
                'W': [1, [207, 270, 342, 467, 462, 797, 710, 239, 374],
                      10, [374, 423, 605, 238, 375, 238, 334, 462],
                      18, 26, 462, 27, 28, 238, 29, 31, 605,
                      32, [344, 748, 684, 560, 695, 739, 563, 511, 729,
                           793, 318, 312, 666, 526, 896, 758, 772, 544,
                           772, 628, 465, 607, 753, 711, 972, 647, 620,
                           607, 374, 333, 374, 606, 500, 239, 417, 503,
                           427, 529, 415, 264, 444, 518, 241, 230, 495,
                           228, 793, 527, 524],
                      81, [524, 504, 338, 336, 277, 517, 450, 652, 466,
                           452, 407, 370, 258, 370, 605]
                      ]
                }] # end descendant fonts
            }
CIDFontInfo['MSung-Light'] =  {'Type':'/Font',
            'Subtype':'/Type0',
            'Name': '/%(internalName)s', #<-- the internal name
            'BaseFont': '/' + 'MSung-Light',
            'Encoding': '/%(encodings)s',
            'DescendantFonts': [{'Type':'/Font',
                'Subtype':'/CIDFontType0',
                'BaseFont':'/'+'MSung-Light',
                'FontDescriptor': {
                    'Type': '/FontDescriptor',
                    'Ascent': 752,
                    'CapHeight': 737,
                    'Descent': -271,
                    'Flags': 6,
                    'FontBBox': [-160, -249, 1015, 888],
                    'FontName': '/'+'MSung-Light',
                    'ItalicAngle': 0,
                    'Leading': 148,
                    'MaxWidth': 1000,
                    'MissingWidth': 500,
                    'StemH': 45,
                    'StemV': 58,
                    'XHeight': 553
                    },
                'CIDSystemInfo': {
                    'Registry': '(Adobe)',
                    'Ordering': '(CNS1)',
                    'Supplement': 1
                    },
                'DW': 1000,
                'W': [1, 2, 250, 3, [408, 668, 490, 875, 698, 250, 240],
                      10, [240, 417, 667, 250, 313, 250, 520, 500],
                      18, 26, 500, 27, 28, 250, 29, 31, 667,
                      32, [396, 921, 677, 615, 719, 760, 625, 552, 771,
                           802, 354],
                      43, [354, 781, 604, 927, 750, 823, 563, 823, 729,
                           542, 698, 771, 729, 948, 771, 677, 635, 344,
                           520, 344, 469, 500, 250, 469, 521, 427, 521,
                           438, 271, 469, 531, 250],
                      75, [250, 458, 240, 802, 531, 500, 521],
                      82, [521, 365, 333, 292, 521, 458, 677, 479, 458,
                           427, 480, 496, 480, 667]]

                }] # end descendant fonts
            }


#this data was derived from the above width information and removes all dependency on CMAP files as long as we only use the unicode fonts.
widthsByUnichar = {}
widthsByUnichar["MSung-Light"] = {u' ': 250, u'$': 490, u'(': 240, u',': 250, u'0': 500, u'4': 500, u'8': 500, u'<': 667, u'@': 921, u'D': 760, u'H': 802, u'L': 604, u'P': 563, u'T': 698, u'X': 771, u'\\': 520, u'`': 250, u'd': 521, u'h': 531, u'l': 240, u'p': 521, u't': 292, u'x': 479, u'|': 496, u'#': 668, u"'": 250, u'+': 667, u'/': 520, u'3': 500, u'7': 500, u';': 250, u'?': 396, u'C': 719, u'G': 771, u'K': 781, u'O': 823, u'S': 542, u'W': 948, u'[': 344, u'_': 500, u'c': 427, u'g': 469, u'k': 458, u'o': 500, u's': 333, u'w': 677, u'{': 480, u'"': 408, u'&': 698, u'*': 417, u'.': 250, u'2': 500, u'6': 500, u':': 250, u'>': 667, u'B': 615, u'F': 552, u'J': 354, u'N': 750, u'R': 729, u'V': 729, u'Z': 635, u'^': 469, u'b': 521, u'f': 271, u'j': 250, u'n': 531, u'r': 365, u'v': 458, u'z': 427, u'~': 667, u'!': 250, u'%': 875, u')': 240, u'-': 313, u'1': 500, u'5': 500, u'9': 500, u'=': 667, u'A': 677, u'E': 625, u'I': 354, u'M': 927, u'Q': 823, u'U': 771, u'Y': 677, u']': 344, u'a': 469, u'e': 438, u'i': 250, u'm': 802, u'q': 521, u'u': 521, u'y': 458, u'}': 480}
widthsByUnichar["HeiseiKakuGo-W5"] = {u'\uff81': 500, u'\uff85': 500, u'\uff89': 500, u'\uff8d': 500, u'\uff91': 500, u'\uff95': 500, u'\uff99': 500, u'\uff9d': 500, u' ': 277, u'$': 668, u'(': 445, u',': 305, u'0': 668, u'\u0332': 668, u'4': 668, u'8': 668, u'<': 668, u'@': 871, u'D': 699, u'H': 687, u'L': 582, u'P': 582, u'T': 641, u'X': 609, u'`': 590, u'\uff62': 500, u'd': 602, u'\uff66': 500, u'h': 582, u'\uff6a': 500, u'l': 234, u'\uff6e': 500, u'p': 602, u'\uff72': 500, u't': 441, u'\uff76': 500, u'x': 531, u'\uff7a': 500, u'|': 246, u'\uff7e': 500, u'\uff82': 500, u'\uff86': 500, u'\uff8a': 500, u'\uff8e': 500, u'\uff92': 500, u'\uff96': 500, u'\uff9a': 500, u'\uff9e': 500, u'#': 668, u"'": 305, u'+': 668, u'/': 539, u'3': 668, u'7': 668, u';': 305, u'?': 566, u'C': 652, u'G': 676, u'K': 664, u'O': 734, u'S': 605, u'W': 945, u'[': 445, u'_': 668, u'\uff61': 500, u'c': 547, u'\uff65': 500, u'g': 609, u'\uff69': 500, u'k': 539, u'\uff6d': 500, u'o': 605, u'\uff71': 500, u's': 508, u'\uff75': 500, u'w': 781, u'\uff79': 500, u'{': 449, u'\uff7d': 500, u'\u0300': 590, u'\uff83': 500, u'\u2002': 500, u'\uff87': 500, u'\uff8b': 500, u'\uff8f': 500, u'\uff93': 500, u'\uff97': 500, u'\uff9b': 500, u'\uff9f': 500, u'"': 500, u'\xa5': 668, u'&': 727, u'*': 508, u'.': 305, u'2': 668, u'6': 668, u':': 305, u'>': 668, u'B': 637, u'F': 555, u'J': 492, u'N': 707, u'\u203e': 500, u'R': 605, u'V': 727, u'Z': 574, u'^': 668, u'b': 609, u'\uff64': 500, u'f': 391, u'\uff68': 500, u'j': 277, u'\uff6c': 500, u'n': 582, u'\uff70': 500, u'r': 387, u'\uff74': 500, u'v': 562, u'\uff78': 500, u'z': 555, u'\uff7c': 500, u'~': 668, u'\uff80': 500, u'\u0303': 668, u'\uff84': 500, u'\uff88': 500, u'\uff8c': 500, u'\u2011': 379, u'\uff90': 500, u'\uff94': 500, u'\uff98': 500, u'\uff9c': 500, u'!': 305, u'%': 906, u')': 445, u'-': 379, u'1': 668, u'5': 668, u'9': 668, u'=': 668, u'A': 727, u'E': 574, u'I': 242, u'M': 789, u'Q': 734, u'U': 668, u'Y': 609, u']': 445, u'a': 555, u'\uff63': 500, u'e': 574, u'\uff67': 500, u'i': 234, u'\uffe8': 500, u'\uff6b': 500, u'm': 895, u'\uff6f': 500, u'q': 602, u'\uff73': 500, u'u': 582, u'\uff77': 500, u'y': 570, u'\uff7b': 500, u'}': 449, u'\uff7f': 500}
widthsByUnichar["HYSMyeongJo-Medium"] = {u' ': 333, u'$': 625, u'(': 500, u',': 291, u'0': 625, u'4': 625, u'8': 625, u'<': 833, u'D': 750, u'H': 791, u'L': 666, u'P': 666, u'T': 791, u'X': 708, u'\\': 375, u'`': 333, u'd': 583, u'h': 583, u'l': 291, u'p': 583, u't': 375, u'x': 625, u'|': 583, u'#': 833, u"'": 250, u'+': 833, u'/': 375, u'3': 625, u'7': 625, u';': 333, u'?': 500, u'C': 708, u'G': 750, u'K': 791, u'O': 750, u'S': 666, u'[': 500, u'_': 500, u'c': 541, u'g': 583, u'k': 583, u'o': 583, u's': 541, u'w': 833, u'{': 583, u'"': 416, u'&': 833, u'*': 500, u'.': 291, u'2': 625, u'6': 625, u':': 333, u'>': 916, u'B': 708, u'F': 666, u'J': 500, u'N': 791, u'R': 708, u'V': 750, u'Z': 666, u'^': 500, u'b': 583, u'f': 375, u'j': 333, u'n': 583, u'r': 458, u'v': 583, u'z': 500, u'~': 750, u'!': 416, u'%': 916, u')': 500, u'-': 833, u'1': 625, u'5': 625, u'9': 625, u'=': 833, u'A': 791, u'E': 708, u'I': 375, u'M': 916, u'Q': 750, u'U': 791, u'Y': 708, u']': 500, u'a': 541, u'e': 583, u'i': 291, u'm': 875, u'q': 583, u'u': 583, u'y': 625, u'}': 583}
widthsByUnichar["STSong-Light"] = {u' ': 207, u'$': 462, u'(': 374, u',': 238, u'0': 462, u'4': 462, u'8': 462, u'<': 605, u'@': 748, u'D': 739, u'H': 793, u'L': 526, u'P': 544, u'T': 607, u'X': 647, u'\\': 333, u'`': 239, u'd': 529, u'h': 518, u'l': 228, u'p': 524, u't': 277, u'x': 466, u'|': 258, u'#': 467, u"'": 239, u'+': 605, u'/': 334, u'3': 462, u'7': 462, u';': 238, u'?': 344, u'C': 695, u'G': 729, u'K': 666, u'O': 772, u'S': 465, u'W': 972, u'[': 374, u'_': 500, u'c': 427, u'g': 444, u'k': 495, u'o': 524, u's': 336, u'w': 652, u'{': 370, u'"': 342, u'&': 710, u'*': 423, u'.': 238, u'2': 462, u'6': 462, u':': 238, u'>': 605, u'B': 560, u'F': 511, u'J': 312, u'N': 758, u'R': 628, u'V': 711, u'Z': 607, u'^': 606, u'b': 503, u'f': 264, u'j': 230, u'n': 527, u'r': 338, u'v': 450, u'z': 407, u'~': 605, u'!': 270, u'%': 797, u')': 374, u'-': 375, u'1': 462, u'5': 462, u'9': 462, u'=': 605, u'A': 684, u'E': 563, u'I': 318, u'M': 896, u'Q': 772, u'U': 753, u'Y': 620, u']': 374, u'a': 417, u'e': 415, u'i': 241, u'm': 793, u'q': 504, u'u': 517, u'y': 452, u'}': 370}
widthsByUnichar["HeiseiMin-W3"] = {u'\uff81': 500, u'\u0302': 333, u'\uff85': 500, u'\u0306': 333, u'\uff89': 500, u'\u030a': 333, u'\uff8d': 500, u'\uff91': 500, u'\ufb02': 556, u'\uff95': 500, u'\uff99': 500, u'\uff9d': 500, u' ': 250, u'\xa3': 500, u'\u2122': 980, u'$': 500, u'(': 333, u'\xab': 500, u',': 250, u'\xaf': 333, u'0': 500, u'\xb3': 300, u'\u0332': 500, u'4': 500, u'\xb7': 250, u'8': 500, u'\xbb': 500, u'<': 564, u'\xbf': 444, u'@': 921, u'\xc3': 722, u'\u0142': 278, u'D': 722, u'\xc7': 667, u'H': 722, u'\xcb': 611, u'L': 611, u'\xcf': 333, u'P': 556, u'\xd3': 722, u'\u0152': 889, u'T': 611, u'X': 722, u'\xdb': 722, u'\\': 278, u'\xdf': 500, u'\uff64': 500, u'`': 333, u'\xe3': 444, u'\uff62': 500, u'd': 500, u'\xe7': 444, u'\uff66': 500, u'h': 500, u'\xeb': 444, u'\uff6a': 500, u'l': 278, u'\xef': 278, u'\uff6e': 500, u'p': 500, u'\xf3': 500, u'\uff72': 500, u't': 278, u'\uff76': 500, u'x': 500, u'\xfb': 500, u'\uff7a': 500, u'|': 200, u'\xff': 500, u'\u017e': 444, u'\u0301': 333, u'\uff82': 500, u'\u0305': 500, u'\uff86': 500, u'\uff8a': 500, u'\uff8e': 500, u'\u2013': 500, u'\uff92': 500, u'\uff96': 500, u'\uff9a': 500, u'\uff9e': 500, u'#': 500, u'\xa4': 500, u"'": 180, u'\u203a': 333, u'+': 564, u'\xac': 564, u'/': 278, u'\u0131': 278, u'3': 500, u'7': 500, u'\xb8': 333, u';': 278, u'\xbc': 750, u'?': 444, u'\u0141': 611, u'\xc0': 722, u'C': 667, u'\xc4': 722, u'G': 722, u'\xc8': 611, u'K': 722, u'\xcc': 333, u'O': 722, u'\xd0': 722, u'S': 556, u'\u2022': 350, u'\xd4': 722, u'W': 944, u'\uff78': 500, u'\xd8': 722, u'[': 333, u'\xdc': 722, u'_': 500, u'\u0161': 389, u'\xe0': 444, u'c': 444, u'\uff65': 500, u'\xe4': 444, u'g': 500, u'\uff69': 500, u'\xe8': 444, u'k': 500, u'\uff6d': 500, u'\xec': 278, u'o': 500, u'\uff71': 500, u'\xf0': 500, u's': 389, u'\uff75': 500, u'\xf4': 500, u'w': 722, u'\uff79': 500, u'\xf8': 500, u'{': 480, u'\uff7e': 500, u'\u017d': 611, u'\xfc': 500, u'\u0300': 333, u'\uff83': 500, u'\u2002': 500, u'\u0304': 333, u'\uff87': 500, u'\u0308': 333, u'\uff8b': 500, u'\u030c': 333, u'\uff8f': 500, u'\uff93': 500, u'\u2012': 500, u'\uff97': 500, u'\uff9b': 500, u'\u201a': 333, u'\uff9f': 500, u'\u201e': 444, u'\xa1': 333, u'"': 408, u'\xa5': 500, u'&': 778, u'\xa9': 760, u'\u0328': 333, u'*': 500, u'\xad': 564, u'.': 250, u'\uffe8': 500, u'2': 500, u'\xb5': 500, u'6': 500, u'\xb9': 300, u':': 278, u'\xbd': 750, u'>': 564, u'\xc1': 722, u'\uff61': 500, u'B': 667, u'\xc5': 722, u'F': 556, u'\xc9': 611, u'J': 389, u'\xcd': 333, u'N': 722, u'\xd1': 722, u'\u203e': 500, u'R': 667, u'\xd5': 722, u'V': 722, u'\xd9': 722, u'Z': 611, u'\xdd': 722, u'^': 469, u'\xe1': 444, u'\u0160': 556, u'b': 500, u'\xe5': 444, u'\u2039': 333, u'f': 333, u'\xe9': 444, u'\uff68': 500, u'j': 278, u'\xed': 278, u'\uff6c': 500, u'n': 500, u'\xf1': 500, u'\uff70': 500, u'r': 333, u'\xf5': 500, u'\uff74': 500, u'v': 500, u'\xf9': 500, u'\u0178': 722, u'z': 444, u'\xfd': 500, u'\uff7c': 500, u'~': 333, u'\uff80': 500, u'\u0303': 333, u'\uff84': 500, u'\u0307': 333, u'\uff88': 500, u'\u030b': 333, u'\uff8c': 500, u'\u2011': 333, u'\uff90': 500, u'\uff94': 500, u'\uff98': 500, u'\uff9c': 500, u'\u2044': 167, u'!': 333, u'\xa2': 500, u'%': 833, u'\u0327': 333, u'\xa6': 200, u')': 333, u'\xaa': 276, u'-': 333, u'\xae': 760, u'1': 500, u'\xb2': 300, u'5': 500, u'9': 500, u'\xba': 310, u'=': 564, u'\xbe': 750, u'A': 722, u'\u01c0': 200, u'\xc2': 722, u'E': 611, u'\xc6': 889, u'I': 333, u'\xca': 611, u'M': 889, u'\xce': 333, u'Q': 722, u'\u0153': 722, u'\xd2': 722, u'U': 722, u'\xd6': 722, u'Y': 722, u'\ufb01': 556, u'\xda': 722, u']': 333, u'\xde': 556, u'a': 444, u'\uff63': 500, u'\xe2': 444, u'e': 444, u'\uff67': 500, u'\xe6': 667, u'i': 278, u'\uff7d': 500, u'\uff6b': 500, u'\xea': 444, u'm': 778, u'\uff6f': 500, u'\xee': 278, u'q': 500, u'\uff73': 500, u'\xf2': 500, u'u': 500, u'\uff77': 500, u'\xf6': 500, u'y': 500, u'\uff7b': 500, u'\xfa': 500, u'}': 480, u'\uff7f': 500, u'\xfe': 500}
widthsByUnichar["HYGothic-Medium"] = {u' ': 500, u'$': 500, u'(': 500, u',': 500, u'0': 500, u'4': 500, u'8': 500, u'<': 500, u'@': 500, u'D': 500, u'H': 500, u'L': 500, u'P': 500, u'T': 500, u'X': 500, u'\\': 500, u'`': 500, u'd': 500, u'h': 500, u'l': 500, u'p': 500, u't': 500, u'x': 500, u'|': 500, u'#': 500, u"'": 500, u'+': 500, u'/': 500, u'3': 500, u'7': 500, u';': 500, u'?': 500, u'C': 500, u'G': 500, u'K': 500, u'O': 500, u'S': 500, u'W': 500, u'[': 500, u'_': 500, u'c': 500, u'g': 500, u'k': 500, u'o': 500, u's': 500, u'w': 500, u'{': 500, u'"': 500, u'&': 500, u'*': 500, u'.': 500, u'2': 500, u'6': 500, u':': 500, u'>': 500, u'B': 500, u'F': 500, u'J': 500, u'N': 500, u'R': 500, u'V': 500, u'Z': 500, u'^': 500, u'b': 500, u'f': 500, u'j': 500, u'n': 500, u'r': 500, u'v': 500, u'z': 500, u'!': 500, u'%': 500, u')': 500, u'-': 500, u'1': 500, u'5': 500, u'9': 500, u'=': 500, u'A': 500, u'E': 500, u'I': 500, u'M': 500, u'Q': 500, u'U': 500, u'Y': 500, u']': 500, u'a': 500, u'e': 500, u'i': 500, u'm': 500, u'q': 500, u'u': 500, u'y': 500, u'}': 500}


#shift-jis saying 'This is Heisei-Minchou'
message1 =  '\202\261\202\352\202\315\225\275\220\254\226\276\222\251\202\305\202\267\201B'
message2 = '\202\261\202\352\202\315\225\275\220\254\212p\203S\203V\203b\203N\202\305\202\267\201B'

##def pswidths(text):
##    words = text.split()
##    out = []
##    for word in words:
##        if word == '[':
##            out.append(word)
##        else:
##            out.append(word + ',')
##    return eval(''.join(out),{})
