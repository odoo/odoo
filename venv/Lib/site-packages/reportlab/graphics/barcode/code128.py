#
# Copyright (c) 2000 Tyler C. Sarna <tsarna@sarna.org>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. All advertising materials mentioning features or use of this software
#    must display the following acknowledgement:
#      This product includes software developed by Tyler C. Sarna.
# 4. Neither the name of the author nor the names of contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

from reportlab.lib.units import inch
from reportlab.lib.utils import asNative
from reportlab.graphics.barcode.common import MultiWidthBarcode
from string import digits

_patterns = {
    0   :   'BaBbBb',    1   :   'BbBaBb',    2   :   'BbBbBa',
    3   :   'AbAbBc',    4   :   'AbAcBb',    5   :   'AcAbBb',
    6   :   'AbBbAc',    7   :   'AbBcAb',    8   :   'AcBbAb',
    9   :   'BbAbAc',    10  :   'BbAcAb',    11  :   'BcAbAb',
    12  :   'AaBbCb',    13  :   'AbBaCb',    14  :   'AbBbCa',
    15  :   'AaCbBb',    16  :   'AbCaBb',    17  :   'AbCbBa',
    18  :   'BbCbAa',    19  :   'BbAaCb',    20  :   'BbAbCa',
    21  :   'BaCbAb',    22  :   'BbCaAb',    23  :   'CaBaCa',
    24  :   'CaAbBb',    25  :   'CbAaBb',    26  :   'CbAbBa',
    27  :   'CaBbAb',    28  :   'CbBaAb',    29  :   'CbBbAa',
    30  :   'BaBaBc',    31  :   'BaBcBa',    32  :   'BcBaBa',
    33  :   'AaAcBc',    34  :   'AcAaBc',    35  :   'AcAcBa',
    36  :   'AaBcAc',    37  :   'AcBaAc',    38  :   'AcBcAa',
    39  :   'BaAcAc',    40  :   'BcAaAc',    41  :   'BcAcAa',
    42  :   'AaBaCc',    43  :   'AaBcCa',    44  :   'AcBaCa',
    45  :   'AaCaBc',    46  :   'AaCcBa',    47  :   'AcCaBa',
    48  :   'CaCaBa',    49  :   'BaAcCa',    50  :   'BcAaCa',
    51  :   'BaCaAc',    52  :   'BaCcAa',    53  :   'BaCaCa',
    54  :   'CaAaBc',    55  :   'CaAcBa',    56  :   'CcAaBa',
    57  :   'CaBaAc',    58  :   'CaBcAa',    59  :   'CcBaAa',
    60  :   'CaDaAa',    61  :   'BbAdAa',    62  :   'DcAaAa',
    63  :   'AaAbBd',    64  :   'AaAdBb',    65  :   'AbAaBd',
    66  :   'AbAdBa',    67  :   'AdAaBb',    68  :   'AdAbBa',
    69  :   'AaBbAd',    70  :   'AaBdAb',    71  :   'AbBaAd',
    72  :   'AbBdAa',    73  :   'AdBaAb',    74  :   'AdBbAa',
    75  :   'BdAbAa',    76  :   'BbAaAd',    77  :   'DaCaAa',
    78  :   'BdAaAb',    79  :   'AcDaAa',    80  :   'AaAbDb',
    81  :   'AbAaDb',    82  :   'AbAbDa',    83  :   'AaDbAb',
    84  :   'AbDaAb',    85  :   'AbDbAa',    86  :   'DaAbAb',
    87  :   'DbAaAb',    88  :   'DbAbAa',    89  :   'BaBaDa',
    90  :   'BaDaBa',    91  :   'DaBaBa',    92  :   'AaAaDc',
    93  :   'AaAcDa',    94  :   'AcAaDa',    95  :   'AaDaAc',
    96  :   'AaDcAa',    97  :   'DaAaAc',    98  :   'DaAcAa',
    99  :   'AaCaDa',    100 :   'AaDaCa',    101 :   'CaAaDa',
    102 :   'DaAaCa',    103 :   'BaAdAb',    104 :   'BaAbAd',
    105 :   'BaAbCb',    106 :   'BcCaAaB'
}

starta, startb, startc, stop = 103, 104, 105, 106

seta = {
        ' ' :   0,        '!' :   1,        '"' :   2,        '#' :   3,
        '$' :   4,        '%' :   5,        '&' :   6,       '\'' :   7,
        '(' :   8,        ')' :   9,        '*' :  10,        '+' :  11,
        ',' :  12,        '-' :  13,        '.' :  14,        '/' :  15,
        '0' :  16,        '1' :  17,        '2' :  18,        '3' :  19,
        '4' :  20,        '5' :  21,        '6' :  22,        '7' :  23,
        '8' :  24,        '9' :  25,        ':' :  26,        ';' :  27,
        '<' :  28,        '=' :  29,        '>' :  30,        '?' :  31,
        '@' :  32,        'A' :  33,        'B' :  34,        'C' :  35,
        'D' :  36,        'E' :  37,        'F' :  38,        'G' :  39,
        'H' :  40,        'I' :  41,        'J' :  42,        'K' :  43,
        'L' :  44,        'M' :  45,        'N' :  46,        'O' :  47,
        'P' :  48,        'Q' :  49,        'R' :  50,        'S' :  51,
        'T' :  52,        'U' :  53,        'V' :  54,        'W' :  55,
        'X' :  56,        'Y' :  57,        'Z' :  58,        '[' :  59,
       '\\' :  60,        ']' :  61,        '^' :  62,        '_' :  63,
     '\x00' :  64,     '\x01' :  65,     '\x02' :  66,     '\x03' :  67,
     '\x04' :  68,     '\x05' :  69,     '\x06' :  70,     '\x07' :  71,
     '\x08' :  72,     '\x09' :  73,     '\x0a' :  74,     '\x0b' :  75,
     '\x0c' :  76,     '\x0d' :  77,     '\x0e' :  78,     '\x0f' :  79,
     '\x10' :  80,     '\x11' :  81,     '\x12' :  82,     '\x13' :  83,
     '\x14' :  84,     '\x15' :  85,     '\x16' :  86,     '\x17' :  87,
     '\x18' :  88,     '\x19' :  89,     '\x1a' :  90,     '\x1b' :  91,
     '\x1c' :  92,     '\x1d' :  93,     '\x1e' :  94,     '\x1f' :  95,
     '\xf3' :  96,     '\xf2' :  97,    'SHIFT' :  98,     'TO_C' :  99,
     'TO_B' : 100,     '\xf4' : 101,     '\xf1' : 102
}

setb = {
        ' ' :   0,        '!' :   1,        '"' :   2,        '#' :   3,
        '$' :   4,        '%' :   5,        '&' :   6,       '\'' :   7,
        '(' :   8,        ')' :   9,        '*' :  10,        '+' :  11,
        ',' :  12,        '-' :  13,        '.' :  14,        '/' :  15,
        '0' :  16,        '1' :  17,        '2' :  18,        '3' :  19,
        '4' :  20,        '5' :  21,        '6' :  22,        '7' :  23,
        '8' :  24,        '9' :  25,        ':' :  26,        ';' :  27,
        '<' :  28,        '=' :  29,        '>' :  30,        '?' :  31,
        '@' :  32,        'A' :  33,        'B' :  34,        'C' :  35,
        'D' :  36,        'E' :  37,        'F' :  38,        'G' :  39,
        'H' :  40,        'I' :  41,        'J' :  42,        'K' :  43,
        'L' :  44,        'M' :  45,        'N' :  46,        'O' :  47,
        'P' :  48,        'Q' :  49,        'R' :  50,        'S' :  51,
        'T' :  52,        'U' :  53,        'V' :  54,        'W' :  55,
        'X' :  56,        'Y' :  57,        'Z' :  58,        '[' :  59,
       '\\' :  60,        ']' :  61,        '^' :  62,        '_' :  63,
        '`' :  64,        'a' :  65,        'b' :  66,        'c' :  67,
        'd' :  68,        'e' :  69,        'f' :  70,        'g' :  71,
        'h' :  72,        'i' :  73,        'j' :  74,        'k' :  75,
        'l' :  76,        'm' :  77,        'n' :  78,        'o' :  79,
        'p' :  80,        'q' :  81,        'r' :  82,        's' :  83,
        't' :  84,        'u' :  85,        'v' :  86,        'w' :  87,
        'x' :  88,        'y' :  89,        'z' :  90,        '{' :  91,
        '|' :  92,        '}' :  93,        '~' :  94,     '\x7f' :  95,
     '\xf3' :  96,     '\xf2' :  97,    'SHIFT' :  98,     'TO_C' :  99,
     '\xf4' : 100,     'TO_A' : 101,     '\xf1' : 102
}

setc = {
    '00': 0, '01': 1, '02': 2, '03': 3, '04': 4,
    '05': 5, '06': 6, '07': 7, '08': 8, '09': 9,
    '10':10, '11':11, '12':12, '13':13, '14':14,
    '15':15, '16':16, '17':17, '18':18, '19':19,
    '20':20, '21':21, '22':22, '23':23, '24':24,
    '25':25, '26':26, '27':27, '28':28, '29':29,
    '30':30, '31':31, '32':32, '33':33, '34':34,
    '35':35, '36':36, '37':37, '38':38, '39':39,
    '40':40, '41':41, '42':42, '43':43, '44':44,
    '45':45, '46':46, '47':47, '48':48, '49':49,
    '50':50, '51':51, '52':52, '53':53, '54':54,
    '55':55, '56':56, '57':57, '58':58, '59':59,
    '60':60, '61':61, '62':62, '63':63, '64':64,
    '65':65, '66':66, '67':67, '68':68, '69':69,
    '70':70, '71':71, '72':72, '73':73, '74':74,
    '75':75, '76':76, '77':77, '78':78, '79':79,
    '80':80, '81':81, '82':82, '83':83, '84':84,
    '85':85, '86':86, '87':87, '88':88, '89':89,
    '90':90, '91':91, '92':92, '93':93, '94':94,
    '95':95, '96':96, '97':97, '98':98, '99':99,

    'TO_B' : 100,    'TO_A' : 101,    '\xf1' : 102
}

setmap = {
    'TO_A' : (seta, setb),
    'TO_B' : (setb, seta),
    'TO_C' : (setc, None),
    'START_A' : (starta, seta, setb),
    'START_B' : (startb, setb, seta),
    'START_C' : (startc, setc, None),
}
cStarts = ('START_B','TO_A','TO_B')
tos = list(setmap.keys())

class Code128(MultiWidthBarcode):
    """
    Code 128 is a very compact symbology that can encode the entire
    128 character ASCII set, plus 4 special control codes,
    (FNC1-FNC4, expressed in the input string as \xf1 to \xf4).
    Code 128 can also encode digits at double density (2 per byte)
    and has a mandatory checksum.  Code 128 is well supported and
    commonly used -- for example, by UPS for tracking labels.
    
    Because of these qualities, Code 128 is probably the best choice
    for a linear symbology today (assuming you have a choice).

    Options that may be passed to constructor:

        value (int, or numeric string. required.):
            The value to encode.
   
        barWidth (float, default .0075):
            X-Dimension, or width of the smallest element
            Minumum is .0075 inch (7.5 mils).
            
        barHeight (float, see default below):
            Height of the symbol.  Default is the height of the two
            bearer bars (if they exist) plus the greater of .25 inch
            or .15 times the symbol's length.

        quiet (bool, default 1):
            Wether to include quiet zones in the symbol.
            
        lquiet (float, see default below):
            Quiet zone size to left of code, if quiet is true.
            Default is the greater of .25 inch, or 10 barWidth
            
        rquiet (float, defaults as above):
            Quiet zone size to right left of code, if quiet is true.
            
    Sources of Information on Code 128:

    http://www.semiconductor.agilent.com/barcode/sg/Misc/code_128.html
    http://www.adams1.com/pub/russadam/128code.html
    http://www.barcodeman.com/c128.html

    Official Spec, "ANSI/AIM BC4-1999, ISS" is available for US$45 from
    http://www.aimglobal.org/aimstore/
    """
    barWidth = inch * 0.0075
    lquiet = None
    rquiet = None
    quiet = 1
    barHeight = None
    def __init__(self, value='', **args):
        value = str(value) if isinstance(value,int) else asNative(value)
            
        for k, v in args.items():
            setattr(self, k, v)

        if self.quiet:
            if self.lquiet is None:
                self.lquiet = max(inch * 0.25, self.barWidth * 10.0)
            if self.rquiet is None:
                self.rquiet = max(inch * 0.25, self.barWidth * 10.0)
        else:
            self.lquiet = self.rquiet = 0.0

        MultiWidthBarcode.__init__(self, value)

    def validate(self):
        vval = ""
        self.valid = 1
        for c in self.value:
            if ord(c) > 127 and c not in '\xf1\xf2\xf3\xf4':
                self.valid = 0
                continue
            vval = vval + c
        self.validated = vval
        return vval


    def _try_TO_C(self, l):
        '''Improved version of old _trailingDigitsToC(self, l) inspired by'''
        i = 0
        nl = []
        while i < len(l):
            startpos = i
            rl = []
            savings = -1 # the TO_C costs one character
            while i < len(l):
                if l[i] in cStarts:
                    j = i
                    break
                elif l[i] == '\xf1':
                    rl.append(l[i])
                    i += 1
                    continue
                elif l[i] in digits \
                    and l[i+1] in digits:
                    rl.append(l[i] + l[i+1])
                    i += 2
                    savings += 1
                    continue
                else:
                    if l[i] in digits and l[i+1]=='STOP':
                        rrl = []
                        rsavings = -1   #we need a TO_C
                        k = i
                        while k>startpos:
                            if l[k]=='\xf1':
                                rrl.append(l[i])
                                k -= 1
                            elif l[k] in digits and l[k-1] in digits:
                                rrl.append(l[k-1]+l[k])
                                rsavings += 1
                                k -= 2
                            else:
                                break
                        rrl.reverse()
                        if rsavings>savings+int(savings>=0 and (startpos and nl[-1] in cStarts))-1:
                            nl += l[startpos]
                            startpos += 1
                            rl = rrl
                            del rrl
                            i += 1
                    break
            ta = not (l[i]=='STOP' or j==i)
            xs = savings>=0 and (startpos and nl[-1] in cStarts)
            if savings+int(xs) > int(ta):
                if xs:
                    toc = nl[-1][:-1]+'C'
                    del nl[-1]
                else:
                    toc = 'TO_C'
                nl += [toc]+rl
                if ta:
                    nl.append('TO'+l[j][-2:])
                nl.append(l[i])
            else:
                nl += l[startpos:i+1]
            i += 1
        return nl

    def encode(self):
        # First, encode using only B
        s = self.validated
        l = ['START_B']
        for c in s:
            if c not in setb:
                l = l + ['TO_A', c, 'TO_B']
            else:
                l.append(c)
        l.append('STOP')

        l = self._try_TO_C(l)

        # Finally, replace START_X,TO_Y with START_Y
        if l[1] in tos:
            l[:2] = ['START_' + l[1][-1]]

#        print repr(l)

        # encode into numbers
        start, set, shset = setmap[l[0]]
        e = [start]
        
        l = l[1:-1]
        while l:
            c = l[0]
            if c == 'SHIFT':
                e = e + [set[c], shset[l[1]]]
                l = l[2:]
            elif c in tos:
                e.append(set[c])
                set, shset = setmap[c]
                l = l[1:]
            else:
                e.append(set[c])
                l = l[1:]

        c = e[0]
        for i in range(1, len(e)):
            c = c + i * e[i]
        self.encoded = e + [c % 103, stop]
        return self.encoded

    def decompose(self):
        self.decomposed = ''.join([_patterns[c] for c in self.encoded])
        return self.decomposed

    def _humanText(self):
        return self.value

class Code128Auto(Code128):
    '''contributed by https://bitbucket.org/kylemacfarlane/
    see https://bitbucket.org/rptlab/reportlab/issues/69/implementations-of-code-128-auto-and-data
    '''
    def encode(self):
        s = self.validated

        current_set = None
        l = []
        value = list(s)
        while value:
            c = value.pop(0)
            if c in digits and value and value[0] in digits:
                c += value.pop(0)

            if c in setc:
                set_ = 'C'
            elif c in setb:
                set_ = 'B'
            else:
                set_ = 'A'

            if current_set != set_:
                if current_set:
                    l.append('TO_' + set_)
                else:
                    l.append('START_' + set_)
                current_set = set_

            l.append(c)
        l.append('STOP')

        start, set, shset = setmap[l[0]]
        e = [start]

        l = l[1:-1]
        while l:
            c = l[0]
            if c == 'SHIFT':
                e = e + [set[c], shset[l[1]]]
                l = l[2:]
            elif c in tos:
                e.append(set[c])
                set, shset = setmap[c]
                l = l[1:]
            else:
                e.append(set[c])
                l = l[1:]

        c = e[0]
        for i in range(1, len(e)):
            c = c + i * e[i]
        self.encoded = e + [c % 103, stop]
        return self.encoded

if __name__=='__main__':
    def main():
        from reportlab.graphics.barcode.code128 import Code128
        from reportlab.platypus import Spacer, SimpleDocTemplate
        from reportlab.lib.units import inch
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus.paragraph import Paragraph
        from reportlab.platypus.flowables import KeepTogether
        styles = getSampleStyleSheet()
        styleN = styles['Normal']
        styleH = styles['Heading1']
        story = []
        storyAdd = story.append
        for s in (
            'BBBB123456BBB',
            'BBBB12345BBB',
            'BBBB1234BBB',
            'BBBB123BBB',
            'BBBB12BBB',
            'BBBB1BBB',
            'BBBB123456aa',
            'BBBB1234aa',
            'BBBB123aa',
            'BBBB12aa',
            'BBBB1aa',
            'BBBB123456',
            'BBBB12345',
            'BBBB1234',
            'BBBB123',
            'BBBB12',
            'BBBB1',
            '\xf11234B',
            'Ba\xf11234B',
            'Ba12',
            'Ba123B',
            'Ba1234B',
            'BBBB1234567',
            'BBBB1234567aa',
            ):
            storyAdd(KeepTogether([Paragraph('Code 128 %r' % s, styleN),Code128(s)]))
            storyAdd(Spacer(inch,inch))
        SimpleDocTemplate('code128-out.pdf').build(story)
    main()
