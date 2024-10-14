__all__=('AcroForm',)
from reportlab.pdfbase.pdfdoc import (PDFObject, PDFArray, PDFDictionary, PDFString, pdfdocEnc,
                                    PDFName, PDFStream, PDFStreamFilterZCompress, escapePDF)
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.colors import Color, CMYKColor, Whiter, Blacker, opaqueColor
from reportlab.lib.rl_accel import fp_str
from reportlab.lib.utils import isStr, asNative
import weakref

visibilities = dict(
                visible=0,
                hidden=0,
                visibleNonPrinting=0,
                hiddenPrintable=0,
                )

orientations = {
                0: [],
                90: [],
                180: [],
                270: [],
                }

#adobe counts bits 1 - 32
fieldFlagValues = dict(
                readOnly = 1<<0,
                required = 1<<1,
                noExport = 1<<2,
                noToggleToOff = 1<<14,
                radio = 1<<15,
                pushButton = 1<<16,
                radiosInUnison = 1<<25,
                #text fields
                multiline = 1<<12,
                password = 1<<13,
                fileSelect = 1<<20,         #1.4
                doNotSpellCheck = 1<<22,    #1.4
                doNotScroll = 1<<23,        #1.4
                comb = 1<<24,               #1.5
                richText = 1<<25,           #1.5

                #choice fields
                combo = 1<<17,
                edit = 1<<18,
                sort = 1<<19,
                multiSelect = 1<<21,        #1.4
                commitOnSelChange = 1<<26,  #1.5
                )

annotationFlagValues = dict(
                    invisible=1<<0,
                    hidden=1<<1,
                    nozoom=1<<3,
                    norotate=1<<4,
                    noview=1<<5,
                    readonly=1<<6,
                    locked=1<<7,            #1.4
                    togglenoview=1<<8,      #1.9
                    lockedcontents=1<<9,    #1.7
                    )
annotationFlagValues['print']=1<<2

_bsStyles = dict(
            solid='S',
            dashed='D',
            bevelled='B',
            inset='I',
            underlined='U',
            )

def bsPDF(borderWidth,borderStyle,dashLen):
    d = dict(W=borderWidth,S=PDFName(_bsStyles[borderStyle]))
    if borderStyle=='dashed':
        if not dashLen:
            dashLen = [3]
        elif not isinstance(dashLen,(list,tuple)):
            dashLen = [dashLen]
        d['D'] = PDFArray(dashLen)
    return PDFDictionary(d)

def escPDF(s):
    return escapePDF(s).replace('%','\\045')

def makeFlags(s,d=annotationFlagValues):
    if not isinstance(s,int):
        v = s
        s = 0
        for x in v.split():
            s |= d[x]
    return s

class PDFFromString(PDFObject):
    def __init__(self,s):
        if not isStr(s):
            raise ValueError('need a unicode/bytes argument not %r' % s)
        self._s = s

    def format(self,document):
        return pdfdocEnc(self._s)

class RadioGroup(PDFObject):
    def __init__(self,name,tooltip='',fieldFlags='noToggleToOff required radio'):
        if not name:
            raise ValueError('RadioGroup created with no name')
        self.TU = tooltip
        self.Ff = makeFlags(fieldFlags,fieldFlagValues)
        self.kids = []
        self.T = name
        self.V = None

    def format(self,doc):
        kids = self.kids
        d = len(kids)
        if d<2: raise ValueError('RadioGroup:%s has %d < 2 RadioBoxes' % (self.T,d))

        d = dict(
                Ff=self.Ff,
                Kids = PDFArray([k for k in self.kids]),
                FT = PDFName('Btn'),
                T = PDFString(self.T),
                #DA = PDFString('0 g'),
                )
        if self.V: d['V'] = PDFName(self.V)
        if self.TU: d['TU'] =PDFString(self.TU)
        r = PDFDictionary(d).format(doc)
        return r


def _pdfObjToStr(obj):
    if isinstance(obj,PDFArray):
        return '[%s]' % ''.join((_pdfObjToStr(e) for e in obj.sequence))
    if isinstance(obj,PDFFromString):
        return obj._s
    return str(obj)

class AcroForm(PDFObject):
    formFontNames = {
        "Helvetica": "Helv",
        "Helvetica-Bold": "HeBo",
        'Courier': "Cour",
        'Courier-Bold': "CoBo",
        'Courier-Oblique': "CoOb",
        'Courier-BoldOblique': "CoBO",
        'Helvetica-Oblique': "HeOb",
        'Helvetica-BoldOblique': "HeBO",
        'Times-Roman': "Time",
        'Times-Bold': "TiBo",
        'Times-Italic': "TiIt",
        'Times-BoldItalic': "TiBI",
        }
    def __init__(self,canv,**kwds):
        self.referenceMap = {}
        self._canv = weakref.ref(canv)
        self.fonts = {}
        self.fields = []
        self._radios = {}
        self._refMap = {}
        self._pdfdocenc = {}
        self.sigFlags = None
        self.extras = {}

    @property
    def canv(self):
        _canv = self._canv()
        if _canv is None:
            raise ValueError('%s.canv is no longer available' % self.__class__.__name__)
        return _canv

    def fontRef(self,f):
        return '/Font << /%s %s >>' % (f,self.fonts[f])

    def format(self,doc):
        d = dict(
                Fields = PDFArray([self.getRef(f) for f in self.fields]),
                )
        if self.sigFlags: d['SigFlags'] = self.sigFlags
        if self.fonts:
            FK = list(sorted(self.fonts.keys()))
            F = [self.fontRef(f) for f in FK]
            d['DA'] = PDFString('/%s 0 Tf 0 g' % FK[0])
            d['DR'] = PDFFromString('<< /Encoding\n<<\n/RLAFencoding\n%s\n>>\n%s\n>>' % (self.encRefStr,'\n'.join(F)))
        d.update(self.extras)
        r = PDFDictionary(d).format(doc)
        return r

    def colorTuple(self,c):
        # ISO-32000-1, Table 189: An array of numbers that shall be in ther
        #  range 0.0 to 1.0 specifying the colour [..]. The number of array
        #  elements determines the colour space in which the colour shall
        #  be defined:
        #  0 No colour; transparent 1 DeviceGray 3 DeviceRGB 4 DeviceCMYK
        if c is None or c.alpha == 0:
            return ()
        return c.cmyk() if isinstance(c,CMYKColor) else c.rgb()

    def streamFillColor(self,c):
        t = self.colorTuple(c)
        return fp_str(*t)+(' k' if len(t)==4 else ' rg')
                    
    def streamStrokeColor(self,c):
        t = self.colorTuple(c)
        return fp_str(*t)+(' K' if len(t)==4 else ' RG')

    def checkboxAP(self,
                key,                    #N/D/R
                value,                  #Yes/Off
                buttonStyle='circle',
                shape='square',
                fillColor=None,
                borderColor=None,
                textColor=None,
                borderWidth=1,
                borderStyle='solid',
                size=20,
                dashLen=3,
                ):
        stream = [].append
        ds = size
        if shape=='square':
            stream('q')
            streamFill = self.streamFillColor(fillColor)
            stream('1 g 1 G %(streamFill)s 0 0 %(size)s %(size)s re f')
            if borderWidth!=None:
                streamStroke = self.streamStrokeColor(borderColor)
                hbw = borderWidth*0.5
                smbw = size - borderWidth
                ds = smbw
                if borderStyle=='underlined':
                    stream('%(streamStroke)s %(borderWidth)s w 0 %(hbw)s m %(size)s %(hbw)s l s')
                elif borderStyle in ('dashed','inset','bevelled','solid'):
                    if borderStyle=='dashed':
                        dash = ' [%s ] 0 d' % fp_str(dashLen)
                    else:
                        dash = ''
                    stream('%(streamStroke)s%(dash)s %(borderWidth)s w %(hbw)s %(hbw)s %(smbw)s %(smbw)s re s')

                if borderStyle in ('bevelled','inset'):
                    _2bw = 2*borderWidth
                    sm2bw = size - _2bw
                    ds = sm2bw
                    bbs0 = Blacker(fillColor,0.5)
                    bbs1 = fillColor
                    if key!='D':
                        bbs0, bbs1 = bbs1, bbs0
                    bbs0 = self.streamFillColor(bbs0)
                    bbs1 = self.streamFillColor(bbs1)
                    stream('%(bbs0)s %(borderWidth)s %(borderWidth)s m %(borderWidth)s %(smbw)s l %(smbw)s %(smbw)s l %(sm2bw)s %(sm2bw)s l %(_2bw)s %(sm2bw)s l %(_2bw)s %(_2bw)s l f %(bbs1)s %(smbw)s %(smbw)s m %(smbw)s %(borderWidth)s l %(borderWidth)s %(borderWidth)s l %(_2bw)s %(_2bw)s l %(sm2bw)s %(_2bw)s l %(sm2bw)s %(sm2bw)s l f')
            stream('Q')
        elif shape=='circle':
            cas = lambda _r,**_casKwds: self.circleArcStream(size,_r,**_casKwds)
            r = size*0.5
            streamFill = self.streamFillColor(fillColor)
            stream('q 1 g 1 G %(streamFill)s')
            stream(cas(r))
            stream('f')
            stream('Q')
            if borderWidth!=None:
                stream('q')
                streamStroke = self.streamStrokeColor(borderColor)
                hbw = borderWidth*0.5
                ds = size - borderWidth
                if borderStyle=='underlined':
                    stream('q %(streamStroke)s %(borderWidth)s w 0 %(hbw)s m %(size)s %(hbw)s l s Q')
                elif borderStyle in ('dashed','inset','bevelled','solid'):
                    if borderStyle=='dashed':
                        dash = ' [3 ] 0 d'
                    else:
                        dash = ''
                    stream('%(streamStroke)s%(dash)s %(borderWidth)s w')
                    stream(cas(r-hbw))
                    stream('s')
                stream('Q')
                if borderStyle in ('bevelled','inset'):
                    _3bwh = 3*hbw
                    ds = size - _3bwh
                    bbs0 = Blacker(fillColor,0.5)
                    bbs1 = Whiter(fillColor,0.5)
                    a0 = (0,1)
                    a1 = (2,3)
                    if borderStyle=='inset':
                        bbs0, bbs1 = bbs1, bbs0
                    if key!='D':
                        bbs0, bbs1 = bbs1, bbs0
                    bbs0 = self.streamStrokeColor(bbs0)
                    bbs1 = self.streamStrokeColor(bbs1)
                    stream('q %(bbs0)s %(borderWidth)s w')
                    stream(cas(r-_3bwh,rotated=True,arcs=a0))
                    stream('S Q %(bbs1)s q')
                    stream(cas(r-_3bwh,rotated=True,arcs=a1))
                    stream('S Q')
        if value=='Yes':
            textFillColor = self.streamFillColor(textColor)
            textStrokeColor = self.streamStrokeColor(textColor)
            stream('q %(textFillColor)s %(textStrokeColor)s')
            cbm = cbmarks[buttonStyle]
            if shape=='circle' and buttonStyle=='circle':
                stream(cas((max(r-(size-ds),1))*0.5))
                stream('f')
            else:
                stream(cbm.scaledRender(size,size-ds))
            stream('Q')
        stream = ('\n'.join(stream.__self__) % vars()).replace('  ',' ').replace('\n\n','\n')
        return self.makeStream(
                size, size, stream,
                Resources = PDFFromString('<< /ProcSet [/PDF] >>'),
                )

    @staticmethod
    def circleArcStream(size, r, arcs=(0,1,2,3), rotated=False):
        R = [].append
        rlen = R.__self__.__len__
        hsize = size * 0.5
        f = size / 20.0
        size *= f 
        hsize *= f 
        r *= f
        cp = fp_str(0.55231 * r)
        r = fp_str(r)
        hsize = fp_str(hsize)
        mx = '0.7071 0.7071 -0.7071 0.7071' if rotated else '1 0 0 1'
        R('%(mx)s %(hsize)s %(hsize)s cm')
        if 0 in arcs:
            if rlen()==1: R('%(r)s 0 m')
            R('%(r)s %(cp)s %(cp)s %(r)s 0 %(r)s c')
        if 1 in arcs:
            if rlen()==1: R('0 %(r)s m')
            R('-%(cp)s %(r)s -%(r)s %(cp)s -%(r)s 0 c')
        if 2 in arcs:
            if rlen()==1: R('-%(r)s 0 m')
            R('-%(r)s -%(cp)s -%(cp)s -%(r)s 0 -%(r)s c')
        if 3 in arcs:
            if rlen()==1: R('0 -%(r)s m')
            R('%(cp)s -%(r)s %(r)s -%(cp)s %(r)s 0 c')
        return '\n'.join(R.__self__) % vars()

    def zdMark(self,c,size,ds,iFontName):
        c = ZDSyms[c]
        W = H = size-ds
        fs = H/1.2
        w = float(stringWidth(c,'ZapfDingbats',fs))
        if w>W:
            fs *= W/w
        dx = ds + 0.5*(W-w)
        dy = 0
        return 'BT %(iFontName)s %(fs)s Tf %(dx)s %(dy)s Td %(fs)s TL (%(c)s) Tj ET' % vars()


    def getRef(self,obj):
        return self.canv._doc.Reference(obj)

    def getRefStr(self,obj):
        return asNative(self.getRef(obj).format(self.canv._doc))

    @staticmethod
    def stdColors(t,b,f):
        if isinstance(f,CMYKColor) or isinstance(t,CMYKColor) or isinstance(b,CMYKColor):
            return (t or CMYKColor(0,0,0,0.9), b or  CMYKColor(0,0,0,0.9), f or CMYKColor(0.12,0.157,0,0))
        else:
            return (t or Color(0.1,0.1,0.1), b or Color(0.1,0.1,0.1), f or Color(0.8,0.843,1))
    
    @staticmethod
    def varyColors(key,t,b,f):
        if key!='N':
            func = Whiter if key=='R' else Blacker
            t,b,f = [func(c,0.9) for c in (t,b,f)]
        return t,b,f

    def checkForceBorder(self,x,y,width,height,forceBorder,shape,borderStyle,borderWidth,borderColor,fillColor):
        if forceBorder:
            canv = self.canv
            canv.saveState()
            canv.resetTransforms()
            if borderWidth!=None:
                hbw = 0.5*borderWidth
                canv.setLineWidth(borderWidth)
                canv.setStrokeColor(borderColor)
                s = 1
            else:
                s = hbw = 0
            width -= 2*hbw
            height -= 2*hbw
            x += hbw
            y += hbw
            canv.setFillColor(fillColor)
            if shape=='square':
                canv.rect(x,y,width,height,stroke=s,fill=1)
            else:
                r = min(width,height) * 0.5
                canv.circle(x+r,y+r,r,stroke=s,fill=1)
            canv.restoreState()

    def checkbox(self,
                checked=False,
                buttonStyle='check',
                shape='square',
                fillColor=None,
                borderColor=None,
                textColor=None,
                borderWidth=1,
                borderStyle='solid',
                size=20,
                x=0,
                y=0,
                tooltip=None,
                name=None,
                annotationFlags='print',
                fieldFlags='required',
                forceBorder=False,
                relative=False,
                dashLen = 3,
                ):
        initialValue = 'Yes' if checked else 'Off'
        textColor,borderColor,fillColor=self.stdColors(textColor,borderColor,fillColor)
        canv = self.canv
        if relative:
            x, y = self.canv.absolutePosition(x,y)
        doc = canv._doc
        AP = {}
        for key in 'NDR':
            APV = {}
            tC,bC,fC = self.varyColors(key,textColor,borderColor,fillColor)
            for value in ('Yes','Off'):
                ap = self.checkboxAP(
                                    key,
                                    value,
                                    buttonStyle=buttonStyle,
                                    shape=shape,
                                    fillColor=fC,
                                    borderColor=bC,
                                    textColor=tC,
                                    borderWidth=borderWidth,
                                    borderStyle=borderStyle,
                                    size=size,
                                    dashLen=dashLen,
                                    )
                if ap._af_refstr in self._refMap:
                    ref = self._refMap[ap._af_refstr]
                else:
                    ref = self.getRef(ap)
                    self._refMap[ap._af_refstr] = ref
                APV[value]=ref
            AP[key] = PDFDictionary(APV)
            del APV
        CB = dict(
                FT = PDFName('Btn'),
                P = doc.thisPageRef(),
                V = PDFName(initialValue),
                AS = PDFName(initialValue),
                #DV = PDFName(initialValue),
                Rect = PDFArray((x,y,x+size,y+size)),
                AP = PDFDictionary(AP),
                Subtype = PDFName('Widget'),
                Type = PDFName('Annot'),
                F = makeFlags(annotationFlags,annotationFlagValues),
                Ff = makeFlags(fieldFlags,fieldFlagValues),
                H=PDFName('N'),
                )
        if tooltip:
            CB['TU'] = PDFString(tooltip)
        if not name:
            name = 'AFF%03d' % len(self.fields)
        if borderWidth: CB['BS'] = bsPDF(borderWidth,borderStyle,dashLen)
        CB['T'] = PDFString(name)
        MK = dict(
                CA='(%s)' % ZDSyms[buttonStyle],
                BC=PDFArray(self.colorTuple(borderColor)),
                BG=PDFArray(self.colorTuple(fillColor)),
                )
        CB['MK'] = PDFDictionary(MK)
        CB = PDFDictionary(CB)
        self.canv._addAnnotation(CB)
        self.fields.append(self.getRef(CB))
        self.checkForceBorder(x,y,size,size,forceBorder,shape,borderStyle,borderWidth,borderColor,fillColor)

    def radio(self,
                value=None,
                selected=False,
                buttonStyle='circle',
                shape='circle',
                fillColor=None,
                borderColor=None,
                textColor=None,
                borderWidth=1,
                borderStyle='solid',
                size=20,
                x=0,
                y=0,
                tooltip=None,
                name=None,
                annotationFlags='print',
                fieldFlags='noToggleToOff required radio',
                forceBorder=False,
                relative=False,
                dashLen=3,
                ):
        if name not in self._radios:
            group = RadioGroup(name,tooltip=tooltip,fieldFlags=fieldFlags)
            group._ref = self.getRef(group)
            self._radios[name] = group
            self.fields.append(group._ref)
        else:
            group = self._radios[name]
            fieldFlags = makeFlags(fieldFlags,fieldFlagValues)
            if fieldFlags!=group.Ff:
                raise ValueError('radio.%s.%s created with different flags' % (name,value))
        if not value:
            raise ValueError('bad value %r for radio.%s' % (value,name))
        initialValue = value if selected else 'Off'
        textColor,borderColor,fillColor=self.stdColors(textColor,borderColor,fillColor)

        if initialValue==value:
            if group.V is not None:
                if group.V!=value:
                    raise ValueError('radio.%s.%s sets initial value conflicting with %s'%(name,value,group.V))
            else:
                group.V = value
        canv = self.canv
        if relative:
            x, y = self.canv.absolutePosition(x,y)
        doc = canv._doc
        AP = {}
        for key in 'NDR':
            APV = {}
            tC,bC,fC = self.varyColors(key,textColor,borderColor,fillColor)
            for v in (value,'Off'):
                ap = self.checkboxAP(
                                    key,
                                    'Yes' if v==value else 'Off',
                                    buttonStyle=buttonStyle,
                                    shape=shape,
                                    fillColor=fC,
                                    borderColor=bC,
                                    textColor=tC,
                                    borderWidth=borderWidth,
                                    borderStyle=borderStyle,
                                    size=size,
                                    dashLen=dashLen,
                                    )
                if ap._af_refstr in self._refMap:
                    ref = self._refMap[ap._af_refstr]
                else:
                    ref = self.getRef(ap)
                    self._refMap[ap._af_refstr] = ref
                APV[v]=ref
            AP[key] = PDFDictionary(APV)
            del APV
        RB = dict(
                FT = PDFName('Btn'),
                P = doc.thisPageRef(),
                AS = PDFName(initialValue),
                #DV = PDFName(initialValue),
                Rect = PDFArray((x,y,x+size,y+size)),
                AP = PDFDictionary(AP),
                Subtype = PDFName('Widget'),
                Type = PDFName('Annot'),
                F = makeFlags(annotationFlags,annotationFlagValues),
                Parent = group._ref,
                #DA = PDFString('1 g '+(self.streamFillColor(fillColor) if fillColor else '-0.25 0.75 -0.25 rg'))
                H=PDFName('N'),
                )
        #RB['T'] = PDFString(name)
        MK = dict(
                CA='(%s)' % ZDSyms[buttonStyle],
                BC=PDFArray(self.colorTuple(borderColor)),
                BG=PDFArray(self.colorTuple(fillColor)),
                )
        if borderWidth: RB['BS'] = bsPDF(borderWidth,borderStyle,dashLen)
        RB['MK'] = PDFDictionary(MK)
        RB = PDFDictionary(RB)
        self.canv._addAnnotation(RB)
        group.kids.append(self.getRef(RB))
        self.checkForceBorder(x,y,size,size,forceBorder,shape,borderStyle,borderWidth,borderColor,fillColor)

    def makeStream(self,
                width,
                height,
                stream,
                **D
                ):
        D['Matrix'] = PDFArray([1.0,0.0,0.0,1.0,0.0,0.0])
        D['BBox'] = PDFArray([0,0,width,height])
        D['Subtype'] = PDFName('Form')
        D['Type'] = PDFName('XObject')
        D['FormType'] = 1

        s = PDFStream(
                PDFDictionary(D),
                stream,
                filters = [PDFStreamFilterZCompress()] if self.canv._doc.compression else None,
                )
        #compute a lookup string
        s._af_refstr = stream+'\n'.join(('%s=%r' % (k,_pdfObjToStr(v)) for k,v in sorted(D.items())))
        return s

    def txAP(self,
                key,                    #N/D/R
                value,
                iFontName,
                rFontName,
                fontSize,
                shape='square',
                fillColor=None,
                borderColor=None,
                textColor=None,
                borderWidth=1,
                borderStyle='solid',
                width=120,
                height=36,
                dashLen=3,
                wkind='textfield',
                labels=[],
                I=[],
                sel_bg='0.600006 0.756866 0.854904 rg',
                sel_fg='0 g',
                ):
        _stream = []
        stream = _stream.append
        if opaqueColor(fillColor):
            streamFill = self.streamFillColor(fillColor)
            stream('%(streamFill)s\n0 0 %(width)s %(height)s re\nf')
        if borderWidth!=None and borderWidth>0 and opaqueColor(borderColor):
            hbw = borderWidth*0.5
            bww = width - borderWidth
            bwh = height - borderWidth
            _2bw = 2*borderWidth
            if borderStyle in ('bevelled','inset'):
                bw2w = width - _2bw
                bw2h = height - _2bw
                if borderStyle == 'bevelled':
                    bbs0 = '1 g'
                    if fillColor or borderColor:
                        bbs1 = '-0.250977 0.749023 -0.250977 rg'
                    else:
                        bbs1 = '.75293 g'
                else:
                    bbs0 = '.501953 g'
                    bbs1 = '.75293 g'
                stream('%(bbs0)s\n%(borderWidth)s %(borderWidth)s m\n%(borderWidth)s %(bwh)s l\n%(bww)s %(bwh)s l\n%(bw2w)s %(bw2h)s l\n%(_2bw)s %(bw2h)s l\n%(_2bw)s %(_2bw)s l\nf\n%(bbs1)s\n%(bww)s %(bwh)s m\n%(bww)s %(borderWidth)s l\n%(borderWidth)s %(borderWidth)s l\n%(_2bw)s %(_2bw)s l\n%(bw2w)s %(_2bw)s l\n%(bw2w)s %(bw2h)s l\nf')
        else:
            hbw = _2bw = borderWidth = 0
            bww = width
            bwh = height
        undash = ''
        if opaqueColor(borderColor) and borderWidth:
            streamStroke = self.streamStrokeColor(borderColor)
            if borderStyle=='underlined':
                stream('%(streamStroke)s %(borderWidth)s w 0 %(hbw)s m %(width)s %(hbw)s l s')
            elif borderStyle in ('dashed','inset','bevelled','solid'):
                if borderStyle=='dashed':
                    dash = '\n[%s ] 0 d\n' % fp_str(dashLen)
                    undash = '[] 0 d'
                else:
                    dash = '\n%s w' % borderWidth
                stream('%(streamStroke)s\n%(dash)s\n%(hbw)s %(hbw)s %(bww)s %(bwh)s re\ns')
        _4bw = 4*borderWidth
        w4bw = width - _4bw
        h4bw = height - _4bw
        textFill = self.streamFillColor(textColor)
        stream('/Tx BMC \nq\n%(_2bw)s %(_2bw)s %(w4bw)s %(h4bw)s re\nW\nn')
        leading = 1.2 * fontSize
        if wkind=='listbox':
            nopts = int(h4bw/leading)
            leading = h4bw/float(nopts)
            if nopts>len(labels):
                i0 = 0
                nopts = len(labels)
            elif len(I)<=1:
                i0 = I[0] if I else 0
                if i0:
                    if i0<nopts:
                        i0 = 0
                    else:
                        i = len(labels) - nopts
                        if i0>=i:
                            i0 = i
            else:   #|I|>1
                if I[1]<nopts:
                    i0 = 0
                else:
                    i0 = I[0]
            y = len(labels)
            i = i0 + nopts
            if i>y: i0 = i - y
            ilim = min(y,i0+nopts)
            if I:
                i = i0
                y = height - _2bw - leading
                stream(sel_bg)
                while i<ilim:
                    if i in I:
                        #draw selected bg
                        stream('%%(_2bw)s %s %%(w4bw)s %%(leading)s re\nf' % fp_str(y))
                    y -= leading
                    i += 1
            i = i0
            y = height - _2bw - fontSize
            stream('0 g\n0 G\n%(undash)s')
            while i<ilim:
                stream('BT')
                if i==i0:
                    stream('/%(iFontName)s %(fontSize)s Tf')
                stream(sel_fg if i in I else '%(textFill)s')
                stream('%%(_4bw)s %s Td\n(%s) Tj' % (fp_str(y),escPDF(labels[i])))
                y -= leading
                i += 1
                stream('ET')
        else:
            stream('0 g\n0 G\n%(undash)s')
            if value:
                stream('BT\n/%(iFontName)s %(fontSize)s Tf\n%(textFill)s')
                stream('1 0 0 1 %%(_4bw)s %s Tm' % fp_str(height - fontSize - _2bw)) 
                for line in value.split('\n'):
                    stream('(%s) Tj\n0 %s Td' % (escPDF(line),fp_str(-leading)))
                #the last change is not needed
                _stream[-1] = _stream[-1][:_stream[-1].rfind('\n')]
                stream('ET')
        leading = fp_str(leading)
        stream('Q\nEMC\n')
        stream = ('\n'.join(_stream) % vars()).replace('  ',' ').replace('\n\n','\n')
        return self.makeStream(
                width, height, stream,
                Resources = PDFFromString('<< /ProcSet [/PDF /Text] /Font %(rFontName)s >>' % vars()),
                )

    def makeFont(self,fontName):
        if fontName is None:
            fontName = 'Helvetica'
        if fontName not in self.formFontNames:
            raise ValueError('form font name, %r, is not one of the standard 14 fonts' % fontName)
        fn = self.formFontNames[fontName]
        ref = self.getRefStr(PDFFromString('<< /BaseFont /%s /Subtype /Type1 /Name /%s /Type /Font /Encoding %s >>' % (
                        fontName,fn,self.encRefStr)))
        if fn not in self.fonts:
            self.fonts[fn] = ref
        return ref, fn

    def _textfield(self,
                value='',
                fillColor=None,
                borderColor=None,
                textColor=None,
                borderWidth=1,
                borderStyle='solid',
                width=120,
                height=36,
                x=0,
                y=0,
                tooltip=None,
                name=None,
                annotationFlags='print',
                fieldFlags='',
                forceBorder=False,
                relative=False,
                maxlen=100,
                fontName=None,
                fontSize=None,
                wkind=None,
                options=None,
                dashLen=3,
                ):
        rFontName, iFontName = self.makeFont(fontName)
        if fontSize is None:
            fontSize = 12
        textColor,borderColor,fillColor=self.stdColors(textColor,borderColor,fillColor)
        canv = self.canv
        if relative:
            x, y = self.canv.absolutePosition(x,y)
        doc = canv._doc
        rFontName = '<</%s %s>>' % (iFontName,rFontName)
        Ff = makeFlags(fieldFlags,fieldFlagValues)
        if wkind!='textfield':
            #options must be a list of pairs (label value)
            #value must be a list of the values
            FT='Ch'
            if wkind=='choice':
                Ff |= fieldFlagValues['combo']  #just in case
            V = []
            Opt = []
            AP = []
            I = []
            TF = []
            if not isinstance(options,(list,tuple)):
                raise TypeError('%s options=%r is wrong type' % (wkind,options))
            for v in options:
                if isStr(v):
                    Opt.append(PDFString(v))
                    l = v
                elif isinstance(v,(list,tuple)):
                    if len(v)==1:
                        v=l=v[0]
                    else:
                        l,v = v
                    Opt.append(PDFArray([PDFString(v),PDFString(l)]))
                else:
                    raise TypeError('%s option %r is wrong type' % (wkind,v))
                AP.append(v)
                TF.append(l)
            Opt = PDFArray(Opt)
            if value:
                if not isinstance(value,(list,tuple)):
                    value = [value]
                for v in value:
                    if v not in AP:
                        if v not in TF:
                            raise ValueError('%s value %r is not in option\nvalues %r\nor labels %r' % (wkind,v,AP,TF))
                        else:
                            v = AP[TF.index(v)]
                    I.append(AP.index(v))
                    V.append(PDFString(v))
                I.sort()
                if not (Ff & fieldFlagValues['multiSelect']) or len(value)==1:
                    if wkind=='choice':
                        value = TF[I[0]]
                    else:
                        value = value[:1]
                    V = V[:1]
                V = V[0] if len(V)==1 else PDFArray(V)
                lbextras = dict(labels=TF,I=I,wkind=wkind)
            else:
                V = PDFString(value)
        else:
            I = Opt = []
            lbextras = {}
            FT='Tx'
            if not isStr(value):
                raise TypeError('textfield value=%r is wrong type' % value)
            V = PDFString(value)
        AP = {}
        for key in 'N':
            tC,bC,fC = self.varyColors(key,textColor,borderColor,fillColor)
            ap = self.txAP(
                            key,
                            value,
                            iFontName,
                            rFontName,
                            fontSize,
                            fillColor=fC,
                            borderColor=bC,
                            textColor=tC,
                            borderWidth=borderWidth,
                            borderStyle=borderStyle,
                            width=width,
                            height=height,
                            dashLen = dashLen,
                            **lbextras
                            )
            if ap._af_refstr in self._refMap:
                ref = self._refMap[ap._af_refstr]
            else:
                ref = self.getRef(ap)
                self._refMap[ap._af_refstr] = ref
            AP[key] = ref

        TF = dict(
                FT = PDFName(FT),
                P = doc.thisPageRef(),
                V = V,
                #AS = PDFName(value),
                DV = V,
                Rect = PDFArray((x,y,x+width,y+height)),
                AP = PDFDictionary(AP),
                Subtype = PDFName('Widget'),
                Type = PDFName('Annot'),
                F = makeFlags(annotationFlags,annotationFlagValues),
                Ff = Ff,
                #H=PDFName('N'),
                DA=PDFString('/%s %d Tf %s' % (iFontName,fontSize, self.streamFillColor(textColor))),
                )
        if Opt: TF['Opt'] = Opt
        if I: TF['I'] = PDFArray(I)
        if maxlen:
            TF['MaxLen'] = maxlen
        if tooltip:
            TF['TU'] = PDFString(tooltip)
        if not name:
            name = 'AFF%03d' % len(self.fields)
        TF['T'] = PDFString(name)
        MK = dict(
                BG=PDFArray(self.colorTuple(fillColor)),
                )
        # Acrobat seems to draw a thin border when BS is defined, so only
        # include this if there actually is a border to draw
        if borderWidth:
            TF['BS'] = bsPDF(borderWidth,borderStyle,dashLen)
            MK['BC'] = PDFArray(self.colorTuple(borderColor))
        TF['MK'] = PDFDictionary(MK)

        TF = PDFDictionary(TF)
        self.canv._addAnnotation(TF)
        self.fields.append(self.getRef(TF))
        self.checkForceBorder(x,y,width,height,forceBorder,'square',borderStyle,borderWidth,borderColor,fillColor)

    def textfield(self,
                value='',
                fillColor=None,
                borderColor=None,
                textColor=None,
                borderWidth=1,
                borderStyle='solid',
                width=120,
                height=36,
                x=0,
                y=0,
                tooltip=None,
                name=None,
                annotationFlags='print',
                fieldFlags='',
                forceBorder=False,
                relative=False,
                maxlen=100,
                fontName=None,
                fontSize=None,
                dashLen=3,
                ):
        return self._textfield(
                value=value,
                fillColor=fillColor,
                borderColor=borderColor,
                textColor=textColor,
                borderWidth=borderWidth,
                borderStyle=borderStyle,
                width=width,
                height=height,
                x=x,
                y=y,
                tooltip=tooltip,
                name=name,
                annotationFlags=annotationFlags,
                fieldFlags=fieldFlags,
                forceBorder=forceBorder,
                relative=relative,
                maxlen=maxlen,
                fontName=fontName,
                fontSize=fontSize,
                dashLen=dashLen,
                wkind='textfield',
                )

    def listbox(self,
                value='',
                fillColor=None,
                borderColor=None,
                textColor=None,
                borderWidth=1,
                borderStyle='solid',
                width=120,
                height=36,
                x=0,
                y=0,
                tooltip=None,
                name=None,
                annotationFlags='print',
                fieldFlags='',
                forceBorder=False,
                relative=False,
                fontName=None,
                fontSize=None,
                dashLen=3,
                maxlen=None,
                options=[],
                ):
        return self._textfield(
                value=value,
                fillColor=fillColor,
                borderColor=borderColor,
                textColor=textColor,
                borderWidth=borderWidth,
                borderStyle=borderStyle,
                width=width,
                height=height,
                x=x,
                y=y,
                tooltip=tooltip,
                name=name,
                annotationFlags=annotationFlags,
                fieldFlags=fieldFlags,
                forceBorder=forceBorder,
                relative=relative,
                maxlen=maxlen,
                fontName=fontName,
                fontSize=fontSize,
                dashLen=dashLen,
                wkind='listbox',
                options = options,
                )
    def choice(self,
                value='',
                fillColor=None,
                borderColor=None,
                textColor=None,
                borderWidth=1,
                borderStyle='solid',
                width=120,
                height=36,
                x=0,
                y=0,
                tooltip=None,
                name=None,
                annotationFlags='print',
                fieldFlags='combo',
                forceBorder=False,
                relative=False,
                fontName=None,
                fontSize=None,
                dashLen=3,
                maxlen=None,
                options=[],
                ):
        return self._textfield(
                value=value,
                fillColor=fillColor,
                borderColor=borderColor,
                textColor=textColor,
                borderWidth=borderWidth,
                borderStyle=borderStyle,
                width=width,
                height=height,
                x=x,
                y=y,
                tooltip=tooltip,
                name=name,
                annotationFlags=annotationFlags,
                fieldFlags=fieldFlags,
                forceBorder=forceBorder,
                relative=relative,
                maxlen=maxlen,
                fontName=fontName,
                fontSize=fontSize,
                dashLen=dashLen,
                wkind='choice',
                options = options,
                )

    def checkboxRelative(self, **kwds):
        "same as checkbox except the x and y are relative to the canvas coordinate transform"
        kwds['relative']=True
        self.checkbox(**kwds)

    def radioRelative(self, **kwds):
        "same as radio except the x and y are relative to the canvas coordinate transform"
        kwds['relative']=True
        self.radio(**kwds)

    def textfieldRelative(self, **kwds):
        "same as textfield except the x and y are relative to the canvas coordinate transform"
        kwds['relative']=True
        self.textfield(**kwds)

    def listboxRelative(self, **kwds):
        "same as textfield except the x and y are relative to the canvas coordinate transform"
        kwds['relative']=True
        self.textfield(**kwds)
    def choiceRelative(self, **kwds):
        "same as textfield except the x and y are relative to the canvas coordinate transform"
        kwds['relative']=True
        self.textfield(**kwds)

    @property
    def encRefStr(self):
        if not self._pdfdocenc:
            self._pdfdocenc = PDFFromString('''<</Type /Encoding /Differences [24 /breve /caron /circumflex /dotaccent /hungarumlaut /ogonek /ring /tilde 39 /quotesingle 96 /grave 128 /bullet /dagger /daggerdbl /ellipsis /emdash /endash /florin /fraction /guilsinglleft /guilsinglright /minus /perthousand /quotedblbase /quotedblleft /quotedblright /quoteleft /quoteright /quotesinglbase /trademark /fi /fl /Lslash /OE /Scaron /Ydieresis /Zcaron /dotlessi /lslash /oe /scaron /zcaron 160 /Euro 164 /currency 166 /brokenbar 168 /dieresis /copyright /ordfeminine 172 /logicalnot /.notdef /registered /macron /degree /plusminus /twosuperior /threesuperior /acute /mu 183 /periodcentered /cedilla /onesuperior /ordmasculine 188 /onequarter /onehalf /threequarters 192 /Agrave /Aacute /Acircumflex /Atilde /Adieresis /Aring /AE /Ccedilla /Egrave /Eacute /Ecircumflex /Edieresis /Igrave /Iacute /Icircumflex /Idieresis /Eth /Ntilde /Ograve /Oacute /Ocircumflex /Otilde /Odieresis /multiply /Oslash /Ugrave /Uacute /Ucircumflex /Udieresis /Yacute /Thorn /germandbls /agrave /aacute /acircumflex /atilde /adieresis /aring /ae /ccedilla /egrave /eacute /ecircumflex /edieresis /igrave /iacute /icircumflex /idieresis /eth /ntilde /ograve /oacute /ocircumflex /otilde /odieresis /divide /oslash /ugrave /uacute /ucircumflex /udieresis /yacute /thorn /ydieresis]>>''')
        return self.getRefStr(self._pdfdocenc)

class CBMark:
    opNames = 'm l c h'.split()
    opCount = 1,1,3,0

    def __init__(self,ops,points,bounds,slack=0.05):
        self.ops = ops
        self.xmin,self.ymin,self.xmax,self.ymax = bounds
        self.points = points
        self.slack = slack

    def scaledRender(self,size,ds=0):
        '''
        >>> print(cbmarks['check'].scaledRender(20))
        12.97075 14.68802 m 15.00139 17.16992 l 15.9039 18.1727 17.93454 18.67409 19.2883 18.67409 c 19.46379 18.27298 l 17.13231 15.51532 l 11.91783 8.62117 l 8.307799 3.030641 l 7.430362 1.526462 l 7.305014 1.275766 7.154596 .97493 6.9039 .824513 c 6.577994 .674095 5.825905 .674095 5.47493 .674095 c 4.672702 .674095 4.497214 .674095 4.321727 .799443 c 4.071031 .97493 3.945682 1.325905 3.770195 1.67688 c 3.218663 2.830084 2.240947 5.337047 2.240947 6.590529 c 2.240947 7.016713 2.491643 7.21727 2.817549 7.442897 c 3.344011 7.818942 4.0961 8.245125 4.747911 8.245125 c 5.249304 8.245125 5.299443 7.818942 5.449861 7.417827 c 5.951253 6.239554 l 6.026462 6.038997 6.252089 5.337047 6.527855 5.337047 c 6.778552 5.337047 7.079387 5.913649 7.179666 6.089136 c 12.97075 14.68802 l h f
        >>> print(cbmarks['cross'].scaledRender(20))
        19.9104 17.43931 m 12.41908 10 l 19.9104 2.534682 l 18.37572 1 l 10.9104 8.491329 l 3.445087 1 l 1.910405 2.534682 l 9.427746 10 l 1.910405 17.46532 l 3.445087 19 l 10.9104 11.50867 l 18.37572 19 l 19.9104 17.43931 l h f
        >>> print(cbmarks['circle'].scaledRender(20))
        1.872576 9.663435 m 1.872576 14.64958 5.936288 18.61357 10.89751 18.61357 c 15.8338 18.61357 19.87258 14.59972 19.87258 9.663435 c 19.87258 4.727147 15.8338 .688366 10.89751 .688366 c 5.936288 .688366 1.872576 4.677285 1.872576 9.663435 c h f
        >>> print(cbmarks['star'].scaledRender(20))
        10.85542 18.3253 m 12.90361 11.84337 l 19.84337 11.84337 l 14.25301 7.650602 l 16.42169 1 l 10.85542 5.096386 l 5.289157 1 l 7.481928 7.650602 l 1.843373 11.84337 l 8.759036 11.84337 l 10.85542 18.3253 l h f
        >>> print(cbmarks['diamond'].scaledRender(20))
        17.43533 9.662031 m 15.63282 7.484006 l 10.85118 .649513 l 8.422809 4.329624 l 5.919332 7.659249 l 4.267038 9.662031 l 6.16968 12.0153 l 10.85118 18.64951 l 12.75382 15.4701 15.00695 12.49096 17.43533 9.662031 c h f
        '''
        #work out the scale and translation
        W = H = size - 2*ds
        xmin = self.xmin
        ymin = self.ymin
        w = self.xmax-xmin
        h = self.ymax-ymin
        slack = self.slack*min(W,H)
        sx = (W - 2*slack)/float(w)
        sy = (H - 2*slack)/float(h)
        sx = sy = min(sx,sy)
        w *= sx
        h *= sy
        dx = ds+(W - w)*0.5
        dy = ds+(H - h)*0.5
        xsc = lambda v: fp_str((v-xmin)*sx+dx)
        ysc = lambda v: fp_str((v-ymin)*sy+dy)

        opNames = self.opNames
        opCount = self.opCount
        C = [].append
        i = 0
        points = self.points
        for op in self.ops:
            c = opCount[op]
            for _ in range(c):
                C(xsc(points[i]))
                C(ysc(points[i+1]))
                i += 2
            C(opNames[op])
        C('f')
        return ' '.join(C.__self__)

cbmarks = dict(
        check=CBMark(
                    [0, 1, 2, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 1, 2, 2, 1, 3],
                    [462, 546, 543, 645, 579, 685, 660, 705, 714, 705, 721, 689, 628, 579, 420, 304, 276, 81, 241, 21, 236, 11, 230, -1, 220, -7, 207, -13, 177, -13, 163, -13, 131, -13, 124, -13, 117, -8, 107, -1, 102, 13, 95, 27, 73, 73, 34, 173, 34, 223, 34, 240, 44, 248, 57, 257, 78, 272, 108, 289, 134, 289, 154, 289, 156, 272, 162, 256, 182, 209, 185, 201, 194, 173, 205, 173, 215, 173, 227, 196, 231, 203, 462, 546],
                    (34,-12,721,706),
                    ),
        cross = CBMark(
                    [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3],
                    [727, 632, 439, 346, 727, 59, 668, 0, 381, 288, 94, 0, 35, 59, 324, 346, 35, 633, 94, 692, 381, 404, 668, 692, 727, 632],
                    (35,0,727,692),
                    ),
        circle = CBMark(
                    [0, 2, 2, 2, 2, 3],
                    [35, 346, 35, 546, 198, 705, 397, 705, 595, 705, 757, 544, 757, 346, 757, 148, 595, -14, 397, -14, 198, -14, 35, 146, 35, 346],
                    (35,-14,757,705),
                    ),
        star = CBMark(
                    [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3],
                    [409, 705, 494, 436, 782, 436, 550, 262, 640, -14, 409, 156, 178, -14, 269, 262, 35, 436, 322, 436, 409, 705],
                    (35,-14,782,705),
                    ),
        diamond = CBMark(
                    [0, 1, 1, 1, 1, 1, 1, 1, 2, 3],
                    [560, 346, 488, 259, 297, -14, 200, 133, 100, 266, 34, 346, 110, 440, 297, 705, 373, 578, 463, 459, 560, 346],
                    (34,-14,560,705),
                    ),
        )
ZDSyms=dict(check='4',cross='5',circle='l',star='N',diamond='u')

if __name__ == "__main__":
    import doctest
    doctest.testmod()
