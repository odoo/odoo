#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/pdfbase/_cidfontdata.py
#$Header $
__version__=''' $Id$ '''
__doc__="""
This defines additional static data to support CID fonts.

Canned data is provided for the Japanese fonts supported by Adobe. We
can add Chinese, Korean and Vietnamese in due course. The data was
extracted by creating very simple postscript documents and running
through Distiller, then examining the resulting PDFs.

Each font is described as a big nested dictionary.  This lets us keep
code out of the module altogether and avoid circular dependencies.

The encoding and font data are grouped by some standard 'language
prefixes':
   chs = Chinese Simplified (mainland)
   cht = Chinese Traditional (Taiwan)
   kor = Korean
   jpn = Japanese
"""


languages = ['jpn', 'kor', 'cht', 'chs']

#breaking down the lists let us check if something is present
#for a specific language
typeFaces_chs = ['STSong-Light'] # to do
typeFaces_cht = ['MSung-Light', 'MHei-Medium'] # to do
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



#shift-jis saying 'This is Heisei-Minchou'
message1 =  '\202\261\202\352\202\315\225\275\220\254\226\276\222\251\202\305\202\267\201B'
message2 = '\202\261\202\352\202\315\225\275\220\254\212p\203S\203V\203b\203N\202\305\202\267\201B'

##def pswidths(text):
##    import string
##    words = string.split(text)
##    out = []
##    for word in words:
##        if word == '[':
##            out.append(word)
##        else:
##            out.append(word + ',')
##    return eval(string.join(out, ''))