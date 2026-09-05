__doc__="""An experimental SVG renderer for the ReportLab graphics framework.

This will create SVG code from the ReportLab Graphics API (RLG).
To read existing SVG code and convert it into ReportLab graphics
objects download the svglib module here:

  http://python.net/~gherman/#svglib
"""

import math, sys, os, codecs, base64
from io import BytesIO, StringIO

from reportlab.pdfbase.pdfmetrics import stringWidth # for font info
from reportlab.lib.rl_accel import fp_str
from reportlab.lib.utils import asNative
from reportlab.graphics.renderbase import getStateDelta, Renderer, renderScaledDrawing
from reportlab.graphics.shapes import STATE_DEFAULTS, Path, UserNode
from reportlab.graphics.shapes import * # (only for test0)
from reportlab import rl_config
from reportlab.lib.utils import RLString, isUnicode, isBytes
from reportlab.pdfgen.canvas import FILL_EVEN_ODD, FILL_NON_ZERO
from .renderPM import _getImage

from xml.dom import getDOMImplementation

### some constants ###

sin = math.sin
cos = math.cos
pi = math.pi

AREA_STYLES = 'stroke-width stroke-linecap stroke stroke-opacity fill fill-opacity stroke-dasharray stroke-dashoffset fill-rule id'.split()
LINE_STYLES = 'stroke-width stroke-linecap stroke stroke-opacity stroke-dasharray stroke-dashoffset id'.split()
TEXT_STYLES = 'font-family font-weight font-style font-variant font-size id'.split()
EXTRA_STROKE_STYLES = 'stroke-width stroke-linecap stroke stroke-opacity stroke-dasharray stroke-dashoffset'.split()
EXTRA_FILL_STYLES = 'fill fill-opacity'.split()

### top-level user function ###
def drawToString(d, showBoundary=rl_config.showBoundary,**kwds):
    "Returns a SVG as a string in memory, without touching the disk"
    s = StringIO()
    drawToFile(d, s, showBoundary=showBoundary,**kwds)
    return s.getvalue()

def drawToFile(d, fn, showBoundary=rl_config.showBoundary,**kwds):
    d = renderScaledDrawing(d)
    c = SVGCanvas((d.width, d.height),**kwds)
    draw(d, c, 0, 0, showBoundary=showBoundary)
    c.save(fn)

def draw(drawing, canvas, x=0, y=0, showBoundary=rl_config.showBoundary):
    """As it says."""
    r = _SVGRenderer()
    r.draw(renderScaledDrawing(drawing), canvas, x, y, showBoundary=showBoundary)

### helper functions ###
def _pointsFromList(L):
    """
    given a list of coordinates [x0, y0, x1, y1....]
    produce a list of points [(x0,y0), (y1,y0),....]
    """

    P=[]
    for i in range(0,len(L), 2):
        P.append((L[i], L[i+1]))

    return P

def transformNode(doc, newTag, node=None, **attrDict):
    """Transform a DOM node into new node and copy selected attributes.

    Creates a new DOM node with tag name 'newTag' for document 'doc'
    and copies selected attributes from an existing 'node' as provided
    in 'attrDict'. The source 'node' can be None. Attribute values will
    be converted to strings.

    E.g.

        n = transformNode(doc, "node1", x="0", y="1")
        -> DOM node for <node1 x="0" y="1"/>

        n = transformNode(doc, "node1", x=0, y=1+1)
        -> DOM node for <node1 x="0" y="2"/>

        n = transformNode(doc, "node1", node0, x="x0", y="x0", zoo=bar())
        -> DOM node for <node1 x="[node0.x0]" y="[node0.y0]" zoo="[bar()]"/>
    """

    newNode = doc.createElement(newTag)
    for newAttr, attr in attrDict.items():
        sattr =  str(attr)
        if not node:
            newNode.setAttribute(newAttr, sattr)
        else:
            attrVal = node.getAttribute(sattr)
            newNode.setAttribute(newAttr, attrVal or sattr)

    return newNode

class EncodedWriter(list):
    '''
    EncodedWriter(encoding) assumes .write will be called with
    either unicode or utf8 encoded bytes. it will accumulate
    unicode
    '''
    BOMS =  {
        'utf-32':codecs.BOM_UTF32,
        'utf-32-be':codecs.BOM_UTF32_BE,
        'utf-32-le':codecs.BOM_UTF32_LE,
        'utf-16':codecs.BOM_UTF16,
        'utf-16-be':codecs.BOM_UTF16_BE,
        'utf-16-le':codecs.BOM_UTF16_LE,
        }
    def __init__(self,encoding,bom=False):
        list.__init__(self)
        self.encoding = encoding = codecs.lookup(encoding).name
        if bom and '16' in encoding or '32' in encoding:
            self.write(self.BOMS[encoding])

    def write(self,u):
        if isBytes(u):
            try:
                 u = u.decode('utf-8')
            except:
                et, ev, tb = sys.exc_info()
                ev = str(ev)
                del et, tb
                raise ValueError("String %r not encoded as 'utf-8'\nerror=%s" % (u,ev))
        elif not isUnicode(u):
            raise ValueError("EncodedWriter.write(%s) argument should be 'utf-8' bytes or str" % ascii(u))
        self.append(u)

    def getvalue(self):
        r = ''.join(self)
        del self[:]
        return r

_fillRuleMap = {
        FILL_NON_ZERO: 'nonzero',
        'non-zero': 'nonzero',
        'nonzero': 'nonzero',
        FILL_EVEN_ODD: 'evenodd',
        'even-odd': 'evenodd',
        'evenodd': 'evenodd',
        }

def py_fp_str(*args):
    return ' '.join((('%f' % a).rstrip('0').rstrip('.') for a in args))

### classes ###
class SVGCanvas:
    def __init__(self, size=(300,300), encoding='utf-8', verbose=0, bom=False, **kwds):
        '''
        verbose = 0 >0 means do verbose stuff
        useClip = False True means don't use a clipPath definition put the global clip into the clip property
                        to get around an issue with safari
        extraXmlDecl = ''   use to add extra xml declarations
        scaleGroupId = ''   id of an extra group to add around the drawing to allow easy scaling
        svgAttrs = {}       dictionary of attributes to be applied to the svg tag itself
        '''
        self.verbose = verbose
        self.encoding = codecs.lookup(encoding).name
        self.bom = bom
        useClip = kwds.pop('useClip',False)
        self.fontHacks = kwds.pop('fontHacks',{})
        self.extraXmlDecl = kwds.pop('extraXmlDecl','')
        scaleGroupId = kwds.pop('scaleGroupId','')
        self._fillMode = FILL_EVEN_ODD

        self.width, self.height = self.size = size
        # self.height = size[1]
        self.code = []
        self.style = {}
        self.path = ''
        self._strokeColor = self._fillColor = self._lineWidth = \
            self._font = self._fontSize = self._lineCap = \
            self._lineJoin = None
        if kwds.pop('use_fp_str',False):
            self.fp_str = fp_str
        else:
            self.fp_str = py_fp_str
        self.cfp_str = lambda *args: self.fp_str(*args).replace(' ',',')

        implementation = getDOMImplementation('minidom')
        #Based on official example here http://www.w3.org/TR/SVG10/linking.html want:
        #<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 20010904//EN" 
        #  "http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd">
        #Thus,
        #doctype = implementation.createDocumentType("svg",
        #          "-//W3C//DTD SVG 20010904//EN",
        #          "http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd")
        #
        #However, putting that example through http://validator.w3.org/ recommends:
        #<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.0//EN" 
        #  "http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd">
        #So we'll use that for our SVG 1.0 output.
        doctype = implementation.createDocumentType("svg",
                  "-//W3C//DTD SVG 1.0//EN",
                  "http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd")
        self.doc = implementation.createDocument(None,"svg",doctype)
        self.svg = self.doc.documentElement
        svgAttrs = dict(
                    width = str(size[0]),
                    height=str(self.height),
                    preserveAspectRatio="xMinYMin meet",
                    viewBox="0 0 %d %d" % (self.width, self.height),
                    #baseProfile = "full",  #disliked in V 1.0

                    #these suggested by Tim Roberts, as updated by peter@maubp.freeserve.co.uk 
                    xmlns="http://www.w3.org/2000/svg",
                    version="1.0",
                    )
        svgAttrs['fill-rule'] = _fillRuleMap[self._fillMode]
        svgAttrs["xmlns:xlink"] = "http://www.w3.org/1999/xlink"
        svgAttrs.update(kwds.pop('svgAttrs',{}))
        for k,v in svgAttrs.items():
            self.svg.setAttribute(k,v)

        title = self.doc.createElement('title')
        text = self.doc.createTextNode('...')
        title.appendChild(text)
        self.svg.appendChild(title)

        desc = self.doc.createElement('desc')
        text = self.doc.createTextNode('...')
        desc.appendChild(text)
        self.svg.appendChild(desc)

        self.setFont(STATE_DEFAULTS['fontName'], STATE_DEFAULTS['fontSize'])
        self.setStrokeColor(STATE_DEFAULTS['strokeColor'])
        self.setLineCap(2)
        self.setLineJoin(0)
        self.setLineWidth(1)

        if not useClip:
            # Add a rectangular clipping path identical to view area.
            clipPath = transformNode(self.doc, "clipPath", id="clip")
            clipRect = transformNode(self.doc, "rect", x=0, y=0,
                width=self.width, height=self.height)
            clipPath.appendChild(clipRect)
            self.svg.appendChild(clipPath)
            gtkw = dict(style="clip-path: url(#clip)")
        else:
            gtkw = dict(clip="0 0 %d %d" % (self.width,self.height))

        self.groupTree = transformNode(self.doc, "g",
            id="group",
            transform="scale(1,-1) translate(0,-%d)" % self.height,
            **gtkw
            )

        if scaleGroupId:
            self.scaleTree = transformNode(self.doc, "g", id=scaleGroupId, transform="scale(1,1)")
            self.scaleTree.appendChild(self.groupTree)
            self.svg.appendChild(self.scaleTree)
        else:
            self.svg.appendChild(self.groupTree)
        self.currGroup = self.groupTree

    def save(self, fn=None):
        writer = EncodedWriter(self.encoding,bom=self.bom)
        self.doc.writexml(writer,addindent="\t",newl="\n",encoding=self.encoding)

        if hasattr(fn,'write'):
            f = fn
        else:
            f = open(fn, 'w',encoding=self.encoding)

        svg = writer.getvalue()
        exd = self.extraXmlDecl
        if exd:
            svg = svg.replace('?>','?>'+exd)
        f.write(svg)
        if f is not fn:
            f.close()

    ### helpers ###
    def NOTUSED_stringWidth(self, s, font=None, fontSize=None):
        """Return the logical width of the string if it were drawn
        in the current font (defaults to self.font).
        """

        font = font or self._font
        fontSize = fontSize or self._fontSize

        return stringWidth(s, font, fontSize)

    def _formatStyle(self, include=[], exclude='',**kwds):
        style = self.style.copy()
        style.update(kwds)
        keys = list(style.keys())
        if include:
            keys = [k for k in keys if k in include]
        if exclude:
            exclude = exclude.split()
            items = [k+': '+str(style[k]) for k in keys if k not in exclude]
        else:
            items = [k+': '+str(style[k]) for k in keys]
        return '; '.join(items) + ';'

    def _escape(self, s):
        '''I don't think this was ever needed; seems to have been copied from renderPS'''
        return s

    def _genArcCode(self, x1, y1, x2, y2, startAng, extent):
        """Calculate the path for an arc inscribed in rectangle defined
        by (x1,y1),(x2,y2)."""

        return

        #calculate semi-minor and semi-major axes of ellipse
        xScale = abs((x2-x1)/2.0)
        yScale = abs((y2-y1)/2.0)
        #calculate centre of ellipse
        x, y = (x1+x2)/2.0, (y1+y2)/2.0

        codeline = 'matrix currentmatrix %s %s translate %s %s scale 0 0 1 %s %s %s setmatrix'

        if extent >= 0:
            arc='arc'
        else:
            arc='arcn'
        data = (x,y, xScale, yScale, startAng, startAng+extent, arc)

        return codeline % data

    def _fillAndStroke(self, code, clip=0, link_info=None,styles=AREA_STYLES,fillMode=None):
        xtra = {}
        if fillMode:
            xtra['fill-rule'] = _fillRuleMap[fillMode]
        path = transformNode(self.doc, "path",
            d=self.path, style=self._formatStyle(styles),
            )
        if link_info :
            path = self._add_link(path, link_info)
        self.currGroup.appendChild(path)
        self.path = ''


    ### styles ###
    def setLineCap(self, v):
        vals = {0:'butt', 1:'round', 2:'square'}
        if self._lineCap != v:
            self._lineCap = v
            self.style['stroke-linecap'] = vals[v]

    def setLineJoin(self, v):
        vals = {0:'miter', 1:'round', 2:'bevel'}
        if self._lineJoin != v:
            self._lineJoin = v
            self.style['stroke-linecap'] = vals[v]

    def setDash(self, array=[], phase=0):
        """Two notations. Pass two numbers, or an array and phase."""

        if isinstance(array,(float,int)):
            self.style['stroke-dasharray'] = ', '.join(map(str, ([array, phase])))
        elif isinstance(array,(tuple,list)) and len(array) > 0:
            assert phase >= 0, "phase is a length in user space"
            self.style['stroke-dasharray'] = ', '.join(map(str, array))
            if phase>0:
                self.style['stroke-dashoffset'] = str(phase)

    def setStrokeColor(self, color):
        self._strokeColor = color
        if color == None:
            self.style['stroke'] = 'none'
        else:
            r, g, b = color.red, color.green, color.blue
            self.style['stroke'] = 'rgb(%d%%,%d%%,%d%%)' % (r*100, g*100, b*100)
            alpha = color.normalizedAlpha
            if alpha!=1:
                self.style['stroke-opacity'] = '%s' % alpha
            elif 'stroke-opacity' in self.style:
                del self.style['stroke-opacity']

    def setFillColor(self, color):
        self._fillColor = color
        if color == None:
            self.style['fill'] = 'none'
        else:
            r, g, b = color.red, color.green, color.blue
            self.style['fill'] = 'rgb(%d%%,%d%%,%d%%)' % (r*100, g*100, b*100)
            alpha = color.normalizedAlpha
            if alpha!=1:
                self.style['fill-opacity'] = '%s' % alpha
            elif 'fill-opacity' in self.style:
                del self.style['fill-opacity']

    def setFillMode(self, v):
        self._fillMode = v
        self.style['fill-rule'] = _fillRuleMap[v]

    def setLineWidth(self, width):
        if width != self._lineWidth:
            self._lineWidth = width
            self.style['stroke-width'] = width

    def setFont(self, font, fontSize):
        if self._font != font or self._fontSize != fontSize:
            self._font = font
            self._fontSize = fontSize
            style = self.style
            for k in TEXT_STYLES:
                if k in style:
                    del style[k]
            svgAttrs = self.fontHacks[font] if font in self.fontHacks else {}
            if isinstance(font,RLString):
                svgAttrs.update(iter(font.svgAttrs.items()))
            if svgAttrs:
                for k,v in svgAttrs.items():
                    a = 'font-'+k
                    if a in TEXT_STYLES:
                        style[a] = v
            if 'font-family' not in style:
                style['font-family'] = font
            style['font-size'] = '%spx' % fontSize

    def _add_link(self, dom_object, link_info) :
        assert isinstance(link_info, dict)
        link = transformNode(self.doc, "a", **link_info)
        link.appendChild(dom_object)
        return link

    ### shapes ###
    def rect(self, x1,y1, x2,y2, rx=8, ry=8, link_info=None, **_svgAttrs):
        "Draw a rectangle between x1,y1 and x2,y2."

        if self.verbose: print("+++ SVGCanvas.rect")

        x = min(x1,x2)
        y = min(y1,y2)
        kwds = {}
        rect = transformNode(self.doc, "rect",
            x=x, y=y, width=max(x1,x2)-x, height=max(y1,y2)-y,
            style=self._formatStyle(AREA_STYLES),**_svgAttrs)

        if link_info :
            rect = self._add_link(rect, link_info)

        self.currGroup.appendChild(rect)

    def roundRect(self, x1,y1, x2,y2, rx=8, ry=8, link_info=None, **_svgAttrs):
        """Draw a rounded rectangle between x1,y1 and x2,y2.

        Corners inset as ellipses with x-radius rx and y-radius ry.
        These should have x1<x2, y1<y2, rx>0, and ry>0.
        """

        rect = transformNode(self.doc, "rect",
            x=x1, y=y1, width=x2-x1, height=y2-y1, rx=rx, ry=ry,
            style=self._formatStyle(AREA_STYLES), **_svgAttrs)

        if link_info:
            rect = self._add_link(rect, link_info)

        self.currGroup.appendChild(rect)

    def drawString(self, s, x, y, angle=0, link_info=None, text_anchor='left', textRenderMode=0, **_svgAttrs):
        if textRenderMode==3: return    #invisible
        s = asNative(s)
        if self.verbose: print("+++ SVGCanvas.drawString")
        needFill = textRenderMode==0 or textRenderMode==2 or textRenderMode==4 or textRenderMode==6
        needStroke = textRenderMode==1 or textRenderMode==2 or textRenderMode==5 or textRenderMode==6

        if (self._fillColor!=None and needFill) or (self._strokeColor!=None and needStroke):
            if not text_anchor in ['start', 'inherited', 'left']:
                textLen = stringWidth(s,self._font,self._fontSize)
                if text_anchor=='end':
                    x -= textLen
                elif text_anchor=='middle':
                    x -= textLen/2.
                elif text_anchor=='numeric':
                    x -= numericXShift(text_anchor,s,textLen,self._font,self._fontSize)
                else:
                    raise ValueError('bad value for text_anchor ' + str(text_anchor))
            s = self._escape(s)
            st = self._formatStyle(TEXT_STYLES)
            if angle != 0:
               st = st + " rotate(%s);" % self.fp_str(angle, x, y)
            if needFill:
                st += self._formatStyle(EXTRA_FILL_STYLES)
            else:
                st += " fill:none;"
            if needStroke:
                st += self._formatStyle(EXTRA_STROKE_STYLES)
            else:
                st += " stroke:none;"
            #if textRenderMode>=4:
            #   _gstate_clipPathSetOrAddself, -1, 1, 0  /*we are adding*/
            text = transformNode(self.doc, "text",
                x=x, y=y, style=st,
                transform="translate(0,%d) scale(1,-1)" % (2*y),
                **_svgAttrs
                )
            content = self.doc.createTextNode(s)
            text.appendChild(content)

            if link_info:
                text = self._add_link(text, link_info)
    
            self.currGroup.appendChild(text)

    def drawCentredString(self, s, x, y, angle=0, text_anchor='middle',
            link_info=None, textRenderMode=0, **_svgAttrs):
        if self.verbose: print("+++ SVGCanvas.drawCentredString")
        self.drawString(s,x,y,angle=angle, link_info=link_info, text_anchor=text_anchor,
                textRenderMode=textRenderMode, **_svgAttrs)

    def drawRightString(self, text, x, y, angle=0,text_anchor='end',
            link_info=None, textRenderMode=0, **_svgAttrs):
        if self.verbose: print("+++ SVGCanvas.drawRightString")
        self.drawString(text,x,y,angle=angle, link_info=link_info, text_anchor=text_anchor,
                textRenderMode=textRenderMode, **_svgAttrs)

    def comment(self, data):
        "Add a comment."

        comment = self.doc.createComment(data)
        # self.currGroup.appendChild(comment)

    def drawImage(self, image, x, y, width, height, embed=True):
        buf = BytesIO()
        image.save(buf,'png')
        buf = asNative(base64.b64encode(buf.getvalue()))
        self.currGroup.appendChild(
                transformNode(self.doc,'image',
                    x=x,y=y,width=width,height=height,
                    href="data:image/png;base64,"+buf,
                    transform="matrix(%s)" % self.cfp_str(1,0,0,-1,0,height+2*y),
                    )
                )

    def line(self, x1, y1, x2, y2):
        if self._strokeColor != None:
            if 0: # something is wrong with line in my SVG viewer...
                line = transformNode(self.doc, "line",
                    x=x1, y=y1, x2=x2, y2=y2,
                    style=self._formatStyle(LINE_STYLES))
                self.currGroup.appendChild(line)
            path = transformNode(self.doc, "path",
                d="M %s L %s Z" % (self.cfp_str(x1,y1),self.cfp_str(x2,y2)),
                style=self._formatStyle(LINE_STYLES))
            self.currGroup.appendChild(path)

    def ellipse(self, x1, y1, x2, y2, link_info=None):
        """Draw an orthogonal ellipse inscribed within the rectangle x1,y1,x2,y2.

        These should have x1<x2 and y1<y2.
        """
        ellipse = transformNode(self.doc, "ellipse",
            cx=(x1+x2)/2.0, cy=(y1+y2)/2.0, rx=(x2-x1)/2.0, ry=(y2-y1)/2.0,
            style=self._formatStyle(AREA_STYLES))

        if link_info:
            ellipse = self._add_link(ellipse, link_info)
            
        self.currGroup.appendChild(ellipse)

    def circle(self, xc, yc, r, link_info=None):
        circle = transformNode(self.doc, "circle",
            cx=xc, cy=yc, r=r,
            style=self._formatStyle(AREA_STYLES))

        if link_info:
            circle = self._add_link(circle, link_info)
        
        self.currGroup.appendChild(circle)

    def drawCurve(self, x1, y1, x2, y2, x3, y3, x4, y4, closed=0):
        pass
        return

        codeline = '%s m %s curveto'
        data = (fp_str(x1, y1), fp_str(x2, y2, x3, y3, x4, y4))
        if self._fillColor != None:
            self.code.append((codeline % data) + ' eofill')
        if self._strokeColor != None:
            self.code.append((codeline % data)
                            + ((closed and ' closepath') or '')
                            + ' stroke')

    def drawArc(self, x1,y1, x2,y2, startAng=0, extent=360, fromcenter=0):
        """Draw a partial ellipse inscribed within the rectangle x1,y1,x2,y2.

        Starting at startAng degrees and covering extent degrees. Angles
        start with 0 to the right (+x) and increase counter-clockwise.
        These should have x1<x2 and y1<y2.
        """

        cx, cy = (x1+x2)/2.0, (y1+y2)/2.0
        rx, ry = (x2-x1)/2.0, (y2-y1)/2.0
        mx = rx * cos(startAng*pi/180) + cx
        my = ry * sin(startAng*pi/180) + cy
        ax = rx * cos((startAng+extent)*pi/180) + cx
        ay = ry * sin((startAng+extent)*pi/180) + cy

        cfp_str = self.cfp_str
        s = [].append
        if fromcenter:
            s("M %s L %s" % (cfp_str(cx, cy), cfp_str(ax, ay)))

        if fromcenter:
            s("A %s %d %d %d %s" % \
              (cfp_str(rx, ry), 0, extent>=180, 0, cfp_str(mx, my)))
        else:
            s("M %s A %s %d %d %d %s Z" % \
              (cfp_str(mx, my), cfp_str(rx, ry), 0, extent>=180, 0, cfp_str(mx, my)))

        if fromcenter:
            s("L %s Z" % cfp_str(cx, cy))

        path = transformNode(self.doc, "path",
            d=' '.join(s.__self__), style=self._formatStyle())
        self.currGroup.appendChild(path)

    def polygon(self, points, closed=0, link_info=None):
        assert len(points) >= 2, 'Polygon must have 2 or more points'

        if self._strokeColor!=None or self._fillColor!=None:
            pts = ', '.join([fp_str(*p) for p in points])
            polyline = transformNode(self.doc, "polygon",
                points=pts, style=self._formatStyle(AREA_STYLES))

            if link_info:
                polyline = self._add_link(polyline, link_info)

            self.currGroup.appendChild(polyline)

        # self._fillAndStroke(polyCode)

    def lines(self, lineList, color=None, width=None):
        # print "### lineList", lineList
        return

        if self._strokeColor != None:
            codeline = '%s m %s l stroke'
            for line in lineList:
                self.code.append(codeline % (fp_str(line[0]), fp_str(line[1])))

    def polyLine(self, points):
        assert len(points) >= 1, 'Polyline must have 1 or more points'

        if self._strokeColor != None:
            pts = ', '.join([fp_str(*p) for p in points])
            polyline = transformNode(self.doc, "polyline",
                points=pts, style=self._formatStyle(AREA_STYLES,fill=None))
            self.currGroup.appendChild(polyline)

    ### groups ###
    def startGroup(self,attrDict=dict(transform="")):
        if self.verbose: print("+++ begin SVGCanvas.startGroup")
        currGroup = self.currGroup
        group = transformNode(self.doc, "g", **attrDict)
        currGroup.appendChild(group)
        self.currGroup = group
        if self.verbose: print("+++ end SVGCanvas.startGroup")
        return currGroup

    def endGroup(self,currGroup):
        if self.verbose: print("+++ begin SVGCanvas.endGroup")
        self.currGroup = currGroup
        if self.verbose: print("+++ end SVGCanvas.endGroup")

    def transform(self, a, b, c, d, e, f):
        if self.verbose: print("!!! begin SVGCanvas.transform", a, b, c, d, e, f)
        tr = self.currGroup.getAttribute("transform")
        if (a, b, c, d, e, f) != (1, 0, 0, 1, 0, 0):
            t = 'matrix(%s)' % self.cfp_str(a,b,c,d,e,f)
            self.currGroup.setAttribute("transform", "%s %s" % (tr, t))

    def translate(self, x, y):
        if (x,y) != (0,0):
            self.currGroup.setAttribute("transform", "%s %s"
                % (self.currGroup.getAttribute("transform"),
                    'translate(%s)' % self.cfp_str(x,y)))

    def scale(self, sx, sy):
        if (sx,sy) != (1,1):
            self.currGroup.setAttribute("transform", "%s %s" 
                    % (self.groups[-1].getAttribute("transform"),
                        'scale(%s)' % self.cfp_str(sx, sy)))

    ### paths ###
    def moveTo(self, x, y):
        self.path = self.path + 'M %s ' % self.fp_str(x, y)

    def lineTo(self, x, y):
        self.path = self.path + 'L %s ' % self.fp_str(x, y)

    def curveTo(self, x1, y1, x2, y2, x3, y3):
        self.path = self.path + 'C %s ' % self.fp_str(x1, y1, x2, y2, x3, y3)

    def closePath(self):
        self.path = self.path + 'Z '

    def saveState(self):
        pass

    def restoreState(self):
        pass

class _SVGRenderer(Renderer):
    """This draws onto an SVG document.
    """

    def __init__(self):
        self.verbose = 0

    def drawNode(self, node):
        """This is the recursive method called for each node in the tree.
        """

        if self.verbose: print("### begin _SVGRenderer.drawNode(%r)" % node)

        self._canvas.comment('begin node %r'%node)
        style = self._canvas.style.copy()
        if not (isinstance(node, Path) and node.isClipPath):
            pass # self._canvas.saveState()

        #apply state changes
        deltas = getStateDelta(node)
        self._tracker.push(deltas)
        self.applyStateChanges(deltas, {})

        #draw the object, or recurse
        self.drawNodeDispatcher(node)

        rDeltas = self._tracker.pop()
        if not (isinstance(node, Path) and node.isClipPath):
            pass #self._canvas.restoreState()
        self._canvas.comment('end node %r'%node)

        #restore things we might have lost (without actually doing anything).
        for k, v in rDeltas.items():
            if k in self._restores:
                setattr(self._canvas,self._restores[k],v)
        self._canvas.style = style

        if self.verbose: print("### end _SVGRenderer.drawNode(%r)" % node)

    _restores = {'strokeColor':'_strokeColor','strokeWidth': '_lineWidth','strokeLineCap':'_lineCap',
                'strokeLineJoin':'_lineJoin','fillColor':'_fillColor','fontName':'_font',
                'fontSize':'_fontSize'}

    def _get_link_info_dict(self, obj):
        #We do not want None or False as the link, even if it is the
        #attribute's value - use the empty string instead.
        url = getattr(obj, "hrefURL", "") or ""
        title = getattr(obj, "hrefTitle", "") or ""
        if url :
            #Is it valid to have a link with no href?  The XML requires
            #the xlink:href to be present, but you might just want a
            #tool tip shown (via the xlink:title attribute).  Note that
            #giving an href of "" is equivalent to "the current page"
            #(a relative link saying go nowhere).
            return {"xlink:href":url, "xlink:title":title, "target":"_top"}
            #Currently of all the mainstream browsers I have tested, only Safari/webkit
            #will show  SVG images embedded in HTML using a simple <img src="..." /> tag.
            #However, the links don't work (Safari 3.2.1 on the Mac).
            #
            #Therefore I use the following, which also works for Firefox, Opera, and
            #IE 6.0 with Adobe SVG Viewer 6 beta:
            #<object data="..." type="image/svg+xml" width="430" height="150" class="img">
            #
            #Once displayed, Firefox and Safari treat the SVG like a frame, and
            #by default clicking on links acts "in frame" and replaces the image.
            #Opera does what I expect, and replaces the whole page with the link.
            #
            #Therefore I use target="_top" to force the links to replace the whole page.
            #This now works as expected on Safari 3.2.1, Firefox 3.0.6, Opera 9.20. 
            #Perhaps the target attribute should be an option, perhaps defaulting to
            #"_top" as used here?
        else :
            return None

    def drawGroup(self, group):
        if self.verbose: print("### begin _SVGRenderer.drawGroup")

        currGroup = self._canvas.startGroup()
        a, b, c, d, e, f = self._tracker.getState()['transform']
        for childNode in group.getContents():
            if isinstance(childNode, UserNode):
                node2 = childNode.provideNode()
            else:
                node2 = childNode
            self.drawNode(node2)
        self._canvas.transform(a, b, c, d, e, f)
        self._canvas.endGroup(currGroup)

        if self.verbose: print("### end _SVGRenderer.drawGroup")

    def drawRect(self, rect):
        link_info = self._get_link_info_dict(rect)
        svgAttrs = getattr(rect,'_svgAttrs',{})
        if rect.rx == rect.ry == 0:
            #plain old rectangle
            self._canvas.rect(
                    rect.x, rect.y,
                    rect.x+rect.width, rect.y+rect.height, link_info=link_info, **svgAttrs)
        else:
            #cheat and assume ry = rx; better to generalize
            #pdfgen roundRect function.  TODO
            self._canvas.roundRect(
                    rect.x, rect.y,
                    rect.x+rect.width, rect.y+rect.height,
                    rect.rx, rect.ry,
                    link_info=link_info, **svgAttrs)

    def drawString(self, stringObj):
        S = self._tracker.getState()
        text_anchor, x, y, text = S['textAnchor'], stringObj.x, stringObj.y, stringObj.text
        self._canvas.drawString(text,x,y,link_info=self._get_link_info_dict(stringObj),
                text_anchor=text_anchor, textRenderMode=getattr(stringObj,'textRenderMode',0),
                    **getattr(stringObj,'_svgAttrs',{}))

    def drawLine(self, line):
        if self._canvas._strokeColor:
            self._canvas.line(line.x1, line.y1, line.x2, line.y2)

    def drawCircle(self, circle):
        self._canvas.circle( circle.cx, circle.cy, circle.r, link_info=self._get_link_info_dict(circle))

    def drawWedge(self, wedge):
        yradius, radius1, yradius1 = wedge._xtraRadii()
        if (radius1==0 or radius1 is None) and (yradius1==0 or yradius1 is None) and not wedge.annular:
            centerx, centery, radius, startangledegrees, endangledegrees = \
             wedge.centerx, wedge.centery, wedge.radius, wedge.startangledegrees, wedge.endangledegrees
            yradius = wedge.yradius or wedge.radius
            (x1, y1) = (centerx-radius, centery-yradius)
            (x2, y2) = (centerx+radius, centery+yradius)
            extent = endangledegrees - startangledegrees
            self._canvas.drawArc(x1, y1, x2, y2, startangledegrees, extent, fromcenter=1)
        else:
            P = wedge.asPolygon()
            if isinstance(P,Path):
                self.drawPath(P)
            else:
                self.drawPolygon(P)

    def drawPolyLine(self, p):
        if self._canvas._strokeColor:
            self._canvas.polyLine(_pointsFromList(p.points))

    def drawEllipse(self, ellipse):
        #need to convert to pdfgen's bounding box representation
        x1 = ellipse.cx - ellipse.rx
        x2 = ellipse.cx + ellipse.rx
        y1 = ellipse.cy - ellipse.ry
        y2 = ellipse.cy + ellipse.ry
        self._canvas.ellipse(x1,y1,x2,y2, link_info=self._get_link_info_dict(ellipse))

    def drawPolygon(self, p):
        self._canvas.polygon(_pointsFromList(p.points), closed=1, link_info=self._get_link_info_dict(p))

    def drawPath(self, path, fillMode=FILL_EVEN_ODD):
        # print "### drawPath", path.points
        from reportlab.graphics.shapes import _renderPath
        c = self._canvas
        drawFuncs = (c.moveTo, c.lineTo, c.curveTo, c.closePath)
        if fillMode is None:
            fillMode = getattr(path,'fillMode',FILL_EVEN_ODD)
        link_info = self._get_link_info_dict(path)
        autoclose = getattr(path,'autoclose','')
        def rP(**kwds):
            return _renderPath(path, drawFuncs, **kwds)
        if autoclose=='svg':
            rP()
            c._fillAndStroke([], clip=path.isClipPath, link_info=link_info, fillMode=fillMode)
        elif autoclose=='pdf':
            rP(forceClose=True)
            c._fillAndStroke([], clip=path.isClipPath, link_info=link_info, fillMode=fillMode)
        else:
            isClosed = rP()
            if not isClosed:
                ofc = c._fillColor
                c.setFillColor(None)
                try:
                    link_info = None
                    c._fillAndStroke([], clip=path.isClipPath, link_info=link_info, fillMode=fillMode)
                finally:
                    c.setFillColor(ofc)
            else:
                c._fillAndStroke([], clip=path.isClipPath, link_info=link_info, fillMode=fillMode)

    def drawImage(self, image):
        path = image.path
        if isinstance(path,str):
            if not (path and os.path.isfile(path)): return
            im = _getImage().open(path)
        elif hasattr(path,'convert'):
            im = path
        else:
            return
        srcW, srcH = im.size
        dstW, dstH = image.width, image.height
        if dstW is None: dstW = srcW
        if dstH is None: dstH = srcH
        self._canvas.drawImage(im, image.x, image.y, dstW, dstH, embed=True)

    def applyStateChanges(self, delta, newState):
        """This takes a set of states, and outputs the operators
        needed to set those properties"""

        for key, value in delta.items():
            if key == 'transform':
                pass
                #self._canvas.transform(value[0], value[1], value[2], value[3], value[4], value[5])
            elif key == 'strokeColor':
                self._canvas.setStrokeColor(value)
            elif key == 'strokeWidth':
                self._canvas.setLineWidth(value)
            elif key == 'strokeLineCap':  #0,1,2
                self._canvas.setLineCap(value)
            elif key == 'strokeLineJoin':
                self._canvas.setLineJoin(value)
            elif key == 'strokeDashArray':
                if value:
                    if isinstance(value,(list,tuple)) and len(value)==2 and isinstance(value[1],(tuple,list)):
                        phase = value[0]
                        value = value[1]
                    else:
                        phase = 0
                    self._canvas.setDash(value,phase)
                else:
                    self._canvas.setDash()
            elif key == 'fillColor':
                self._canvas.setFillColor(value)
            elif key in ['fontSize', 'fontName']:
                fontname = delta.get('fontName', self._canvas._font)
                fontsize = delta.get('fontSize', self._canvas._fontSize)
                self._canvas.setFont(fontname, fontsize)
            elif key == 'fillMode':
                self._canvas.setFillMode(value)

def test(outDir='out-svg'):
    # print all drawings and their doc strings from the test
    # file
    if not os.path.isdir(outDir):
        os.mkdir(outDir)
    #grab all drawings from the test module
    from reportlab.graphics import testshapes
    drawings = []

    for funcname in dir(testshapes):
        if funcname[0:10] == 'getDrawing':
            func = getattr(testshapes,funcname)
            drawing = func()
            docstring = getattr(func,'__doc__','')
            drawings.append((drawing, docstring))

    i = 0
    for (d, docstring) in drawings:
        filename = os.path.join(outDir,'renderSVG_%d.svg' % i)
        drawToFile(d, filename)
        i += 1

    from reportlab.graphics.testshapes import getDrawing01
    d = getDrawing01()
    drawToFile(d, os.path.join(outDir,"test.svg"))

    from reportlab.lib.corp import RL_CorpLogo
    from reportlab.graphics.shapes import Drawing

    rl = RL_CorpLogo()
    d = Drawing(rl.width,rl.height)
    d.add(rl)
    drawToFile(d, os.path.join(outDir,"corplogo.svg"))

if __name__=='__main__':
    test()
