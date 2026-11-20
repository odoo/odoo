#this is the interface module that imports all from the C extension _rl_accel
_c_funcs = {}
_py_funcs = {}
### NOTE!  FP_STR SHOULD PROBABLY ALWAYS DO A PYTHON STR() CONVERSION ON ARGS
### IN CASE THEY ARE "LAZY OBJECTS".  ACCELLERATOR DOESN'T DO THIS (YET)
__all__ = list(filter(None,'''
        fp_str
        unicode2T1
        instanceStringWidthT1
        instanceStringWidthTTF
        asciiBase85Encode
        asciiBase85Decode
        escapePDF
        sameFrag
        calcChecksum
        add32
        hex32
        '''.split()))
import reportlab
testing = getattr(reportlab,'_rl_testing',False)
del reportlab

for fn in __all__:
    D={}
    try:
        exec('from reportlab.lib._rl_accel import %s as f' % fn,D)
        _c_funcs[fn] = D['f']
        if testing: _py_funcs[fn] = None
    except ImportError:
        _py_funcs[fn] = None
    del D

if _py_funcs:
    from reportlab.lib.utils import isUnicode, isSeq, rawBytes, asNative, asBytes
    from math import log
    from struct import unpack

if 'fp_str' in _py_funcs:
    _log_10 = lambda x,log=log,_log_e_10=log(10.0): log(x)/_log_e_10
    _fp_fmts = "%.0f", "%.1f", "%.2f", "%.3f", "%.4f", "%.5f", "%.6f"
    def fp_str(*a):
        '''convert separate arguments (or single sequence arg) into space separated numeric strings'''
        if len(a)==1 and isSeq(a[0]): a = a[0]
        s = []
        A = s.append
        for i in a:
            sa =abs(i)
            if sa<=1e-7: A('0')
            else:
                l = sa<=1 and 6 or min(max(0,(6-int(_log_10(sa)))),6)
                n = _fp_fmts[l]%i
                if l:
                    j = len(n)
                    while j:
                        j -= 1
                        if n[j]!='0':
                            if n[j]!='.': j += 1
                            break
                    n = n[:j]
                A((n[0]!='0' or len(n)==1) and n or n[1:])
        return ' '.join(s)

    #hack test for comma users
    if ',' in fp_str(0.25):
        _FP_STR = _fp_str
        def _fp_str(*a):
            return _FP_STR(*a).replace(',','.')
    _py_funcs['fp_str'] = fp_str

if 'unicode2T1' in _py_funcs:
    def unicode2T1(utext,fonts):
        '''return a list of (font,string) pairs representing the unicode text'''
        R = []
        font, fonts = fonts[0], fonts[1:]
        enc = font.encName
        if 'UCS-2' in enc:
            enc = 'UTF16'
        while utext:
            try:
                if isUnicode(utext):
                    s = utext.encode(enc)
                else:
                    s = utext
                R.append((font,s))
                break
            except UnicodeEncodeError as e:
                i0, il = e.args[2:4]
                if i0:
                    R.append((font,utext[:i0].encode(enc)))
                if fonts:
                    R.extend(unicode2T1(utext[i0:il],fonts))
                else:
                    R.append((font._notdefFont,font._notdefChar*(il-i0)))
                utext = utext[il:]
        return R
    _py_funcs['unicode2T1'] = unicode2T1

if 'instanceStringWidthT1' in _py_funcs:
    def instanceStringWidthT1(self, text, size, encoding='utf8'):
        """This is the "purist" approach to width"""
        if not isUnicode(text): text = text.decode(encoding)
        return sum([sum(map(f.widths.__getitem__,t)) for f, t in unicode2T1(text,[self]+self.substitutionFonts)])*0.001*size
    _py_funcs['instanceStringWidthT1'] = instanceStringWidthT1

if 'instanceStringWidthTTF' in _py_funcs:
    def instanceStringWidthTTF(self, text, size, encoding='utf-8'):
        "Calculate text width"
        if not isUnicode(text):
            text = text.decode(encoding or 'utf-8')
        g = self.face.charWidths.get
        dw = self.face.defaultWidth
        return 0.001*size*sum([g(ord(u),dw) for u in text])
    _py_funcs['instanceStringWidthTTF'] = instanceStringWidthTTF

if 'hex32' in _py_funcs:
    def hex32(i):
        return '0X%8.8X' % (int(i)&0xFFFFFFFF)
    _py_funcs['hex32'] = hex32

if 'add32' in _py_funcs:
    def add32(x, y):
        "Calculate (x + y) modulo 2**32"
        return (x+y) & 0xFFFFFFFF
    _py_funcs['add32'] = add32

if 'calcChecksum' in _py_funcs:
    def calcChecksum(data):
        """Calculates TTF-style checksums"""
        data = rawBytes(data)
        if len(data)&3: data = data + (4-(len(data)&3))*b"\0"
        return sum(unpack(">%dl" % (len(data)>>2), data)) & 0xFFFFFFFF
    _py_funcs['calcChecksum'] = calcChecksum

if 'escapePDF' in _py_funcs:
    _ESCAPEDICT={}
    for c in range(256):
        if c<32 or c>=127:
            _ESCAPEDICT[c]= '\\%03o' % c
        elif c in (ord('\\'),ord('('),ord(')')):
            _ESCAPEDICT[c] = '\\'+chr(c)
        else:
            _ESCAPEDICT[c] = chr(c)
    del c
    #Michael Hudson donated this
    def escapePDF(s):
        r = []
        for c in s:
            if not type(c) is int:
                c = ord(c)
            r.append(_ESCAPEDICT[c])
        return ''.join(r)
    _py_funcs['escapePDF'] = escapePDF

if 'asciiBase85Encode' in _py_funcs:
    def asciiBase85Encode(input):
        """Encodes input using ASCII-Base85 coding.

        This is a compact encoding used for binary data within
        a PDF file.  Four bytes of binary data become five bytes of
        ASCII.  This is the default method used for encoding images."""
        doOrd =  isUnicode(input)
        # special rules apply if not a multiple of four bytes.
        whole_word_count, remainder_size = divmod(len(input), 4)
        cut = 4 * whole_word_count
        body, lastbit = input[0:cut], input[cut:]

        out = [].append
        for i in range(whole_word_count):
            offset = i*4
            b1 = body[offset]
            b2 = body[offset+1]
            b3 = body[offset+2]
            b4 = body[offset+3]
            if doOrd:
                b1 = ord(b1)
                b2 = ord(b2)
                b3 = ord(b3)
                b4 = ord(b4)

            if b1<128:
                num = (((((b1<<8)|b2)<<8)|b3)<<8)|b4
            else:
                num = 16777216 * b1 + 65536 * b2 + 256 * b3 + b4

            if num == 0:
                #special case
                out('z')
            else:
                #solve for five base-85 numbers
                temp, c5 = divmod(num, 85)
                temp, c4 = divmod(temp, 85)
                temp, c3 = divmod(temp, 85)
                c1, c2 = divmod(temp, 85)
                assert ((85**4) * c1) + ((85**3) * c2) + ((85**2) * c3) + (85*c4) + c5 == num, 'dodgy code!'
                out(chr(c1+33))
                out(chr(c2+33))
                out(chr(c3+33))
                out(chr(c4+33))
                out(chr(c5+33))

        # now we do the final bit at the end.  I repeated this separately as
        # the loop above is the time-critical part of a script, whereas this
        # happens only once at the end.

        #encode however many bytes we have as usual
        if remainder_size > 0:
            lastbit += (4-len(lastbit))*('\0' if doOrd else b'\000')
            b1 = lastbit[0]
            b2 = lastbit[1]
            b3 = lastbit[2]
            b4 = lastbit[3]
            if doOrd:
                b1 = ord(b1)
                b2 = ord(b2)
                b3 = ord(b3)
                b4 = ord(b4)

            num = 16777216 * b1 + 65536 * b2 + 256 * b3 + b4

            #solve for c1..c5
            temp, c5 = divmod(num, 85)
            temp, c4 = divmod(temp, 85)
            temp, c3 = divmod(temp, 85)
            c1, c2 = divmod(temp, 85)

            #print 'encoding: %d %d %d %d -> %d -> %d %d %d %d %d' % (
            #    b1,b2,b3,b4,num,c1,c2,c3,c4,c5)
            lastword = chr(c1+33) + chr(c2+33) + chr(c3+33) + chr(c4+33) + chr(c5+33)
            #write out most of the bytes.
            out(lastword[0:remainder_size + 1])

        #terminator code for ascii 85
        out('~>')
        return ''.join(out.__self__)
    _py_funcs['asciiBase85Encode'] = asciiBase85Encode

if 'asciiBase85Decode' in _py_funcs:
    def asciiBase85Decode(input):
        """Decodes input using ASCII-Base85 coding.

        This is not normally used - Acrobat Reader decodes for you
        - but a round trip is essential for testing."""
        #strip all whitespace
        stripped = ''.join(asNative(input).split())
        #check end
        assert stripped[-2:] == '~>', 'Invalid terminator for Ascii Base 85 Stream'
        stripped = stripped[:-2]  #chop off terminator

        #may have 'z' in it which complicates matters - expand them
        stripped = stripped.replace('z','!!!!!')
        # special rules apply if not a multiple of five bytes.
        whole_word_count, remainder_size = divmod(len(stripped), 5)
        #print '%d words, %d leftover' % (whole_word_count, remainder_size)
        #assert remainder_size != 1, 'invalid Ascii 85 stream!'
        cut = 5 * whole_word_count
        body, lastbit = stripped[0:cut], stripped[cut:]

        out = [].append
        for i in range(whole_word_count):
            offset = i*5
            c1 = ord(body[offset]) - 33
            c2 = ord(body[offset+1]) - 33
            c3 = ord(body[offset+2]) - 33
            c4 = ord(body[offset+3]) - 33
            c5 = ord(body[offset+4]) - 33

            num = ((85**4) * c1) + ((85**3) * c2) + ((85**2) * c3) + (85*c4) + c5

            temp, b4 = divmod(num,256)
            temp, b3 = divmod(temp,256)
            b1, b2 = divmod(temp, 256)

            assert  num == 16777216 * b1 + 65536 * b2 + 256 * b3 + b4, 'dodgy code!'
            out(chr(b1))
            out(chr(b2))
            out(chr(b3))
            out(chr(b4))

        #decode however many bytes we have as usual
        if remainder_size > 0:
            while len(lastbit) < 5:
                lastbit = lastbit + '!'
            c1 = ord(lastbit[0]) - 33
            c2 = ord(lastbit[1]) - 33
            c3 = ord(lastbit[2]) - 33
            c4 = ord(lastbit[3]) - 33
            c5 = ord(lastbit[4]) - 33
            num = (((85*c1+c2)*85+c3)*85+c4)*85 + (c5
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
            out(lastword)

        r = ''.join(out.__self__)
        return asBytes(r,enc='latin1')
    _py_funcs['asciiBase85Decode'] = asciiBase85Decode

if 'sameFrag' in _py_funcs:
    def sameFrag(f,g):
        'returns 1 if two ParaFrags map out the same'
        if (hasattr(f,'cbDefn') or hasattr(g,'cbDefn')
                or hasattr(f,'lineBreak') or hasattr(g,'lineBreak')): return 0
        for a in ('fontName', 'fontSize', 'textColor', 'rise', 'us_lines', 'link', "backColor", "nobr"):
            if getattr(f,a,None)!=getattr(g,a,None): return 0
        return 1
    _py_funcs['sameFrag'] = sameFrag

G=globals()
for fn in __all__:
    f = _c_funcs[fn] if fn in _c_funcs else _py_funcs[fn]
    if not f:
        raise RuntimeError('function %s is not properly defined' % fn)
    G[fn] = f
del fn, f, G

if __name__=='__main__':
    import sys, subprocess
    for modname in 'reportlab.lib.rl_accel','reportlab.lib._rl_accel':
        for cmd  in (
            #"unicode2T1('abcde fghi . jkl ; mno',fonts)",
            #"unicode2T1(u'abcde fghi . jkl ; mno',fonts)",
            "instanceStringWidthT1(font,'abcde fghi . jkl ; mno',10)",
            "instanceStringWidthT1(font,u'abcde fghi . jkl ; mno',10)",
            ):
            print('%s %s' % (modname,cmd))
            s=';'.join((
                "from reportlab.pdfbase.pdfmetrics import getFont",
                "from %s import unicode2T1,instanceStringWidthT1" % modname,
                "fonts=[getFont('Helvetica')]+getFont('Helvetica').substitutionFonts""",
                "font=fonts[0]",
                ))
            subprocess.check_call([sys.executable,'-mtimeit','-s',s,cmd])
