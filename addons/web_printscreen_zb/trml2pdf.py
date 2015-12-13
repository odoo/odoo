# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2013 ZestyBeanz Technologies Pvt. Ltd.
#    (http://wwww.zbeanztech.com)
#    contact@zbeanztech.com
#    prajul@zbeanztech.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


import sys
import copy
import reportlab
import re
from reportlab.pdfgen import canvas
from reportlab import platypus
from openerp.report.render.rml2pdf import utils
from openerp.report.render.rml2pdf import color
import os
import logging
from lxml import etree
import base64
from reportlab.platypus.doctemplate import ActionFlowable
from openerp.tools.safe_eval import safe_eval as eval
from reportlab.lib.units import inch,cm,mm
from openerp.tools.misc import file_open
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import A4, letter

try:
    from cStringIO import StringIO
    _hush_pyflakes = [ StringIO ]
except ImportError:
    from StringIO import StringIO

_logger = logging.getLogger(__name__)

encoding = 'utf-8'

def _open_image(filename, path=None):
    """Attempt to open a binary file and return the descriptor
    """
    if os.path.isfile(filename):
        return open(filename, 'rb')
    for p in (path or []):
        if p and os.path.isabs(p):
            fullpath = os.path.join(p, filename)
            if os.path.isfile(fullpath):
                return open(fullpath, 'rb')
        try:
            if p:
                fullpath = os.path.join(p, filename)
            else:
                fullpath = filename
            return file_open(fullpath)
        except IOError:
            pass
    raise IOError("File %s cannot be found in image path" % filename)

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._codes = []
        self._flag=False
        self._pageCount=0
        self._currentPage =0
        self._pageCounter=0
        self.pages={}

    def showPage(self):
        self._currentPage +=1
        if not self._flag:
            self._pageCount += 1
        else:
            self.pages.update({self._currentPage:self._pageCount})
        self._codes.append({'code': self._code, 'stack': self._codeStack})
        self._startPage()
        self._flag=False

    def pageCount(self):
        if self.pages.get(self._pageCounter,False):
            self._pageNumber=0
        self._pageCounter +=1
        key=self._pageCounter
        if not self.pages.get(key,False):
            while not self.pages.get(key,False):
                key += 1
        self.setFont("Helvetica", 8)
        self.drawRightString((self._pagesize[0]-30), (self._pagesize[1]-40),
            " %(this)i / %(total)i" % {
               'this': self._pageNumber+1,
               'total': self.pages.get(key,False),
            }
        )

    def save(self):
        """add page info to each page (page x of y)"""
        # reset page counter
        self._pageNumber = 0
        for code in self._codes:
            self._code = code['code']
            self._codeStack = code['stack']
            self.pageCount()
            canvas.Canvas.showPage(self)
#        self.restoreState()
        self._doc.SaveToFile(self._filename, self)

class PageCount(platypus.Flowable):
    def __init__(self, story_count=0):
        platypus.Flowable.__init__(self)
        self.story_count = story_count

    def draw(self):
        self.canv.beginForm("pageCount%d" % self.story_count)
        self.canv.setFont("Helvetica", utils.unit_get(str(8)))
        self.canv.drawString(0, 0, str(self.canv.getPageNumber()))
        self.canv.endForm()

class PageReset(platypus.Flowable):
    def draw(self):
        self.canv._doPageReset = True
class PageReset(platypus.Flowable):
    def draw(self):
        self.canv._doPageReset = True

class _rml_styles(object,):
    def __init__(self, nodes, localcontext):
        self.localcontext = localcontext
        self.styles = {}
        self.styles_obj = {}
        self.names = {}
        self.table_styles = {}
        self.default_style = reportlab.lib.styles.getSampleStyleSheet()

        for node in nodes:
            for style in node.findall('blockTableStyle'):
                self.table_styles[style.get('id')] = self._table_style_get(style)
            for style in node.findall('paraStyle'):
                sname = style.get('name')
                self.styles[sname] = self._para_style_update(style)

                self.styles_obj[sname] = reportlab.lib.styles.ParagraphStyle(sname, self.default_style["Normal"], **self.styles[sname])

            for variable in node.findall('initialize'):
                for name in variable.findall('name'):
                    self.names[ name.get('id')] = name.get('value')

    def _para_style_update(self, node):
        data = {}
        for attr in ['textColor', 'backColor', 'bulletColor', 'borderColor']:
            if node.get(attr):
                data[attr] = color.get(node.get(attr))
        for attr in ['fontName', 'bulletFontName', 'bulletText']:
            if node.get(attr):
                data[attr] = node.get(attr)
        for attr in ['fontSize', 'leftIndent', 'rightIndent', 'spaceBefore', 'spaceAfter',
            'firstLineIndent', 'bulletIndent', 'bulletFontSize', 'leading',
            'borderWidth','borderPadding','borderRadius']:
            if node.get(attr):
                data[attr] = utils.unit_get(node.get(attr))
        if node.get('alignment'):
            align = {
                'right':reportlab.lib.enums.TA_RIGHT,
                'center':reportlab.lib.enums.TA_CENTER,
                'justify':reportlab.lib.enums.TA_JUSTIFY
            }
            data['alignment'] = align.get(node.get('alignment').lower(), reportlab.lib.enums.TA_LEFT)
        return data

    def _table_style_get(self, style_node):
        styles = []
        for node in style_node:
            start = utils.tuple_int_get(node, 'start', (0,0) )
            stop = utils.tuple_int_get(node, 'stop', (-1,-1) )
            if node.tag=='blockValign':
                styles.append(('VALIGN', start, stop, str(node.get('value'))))
            elif node.tag=='blockFont':
                styles.append(('FONT', start, stop, str(node.get('name'))))
            elif node.tag=='blockTextColor':
                styles.append(('TEXTCOLOR', start, stop, color.get(str(node.get('colorName')))))
            elif node.tag=='blockLeading':
                styles.append(('LEADING', start, stop, utils.unit_get(node.get('length'))))
            elif node.tag=='blockAlignment':
                styles.append(('ALIGNMENT', start, stop, str(node.get('value'))))
            elif node.tag=='blockSpan':
                styles.append(('SPAN', start, stop))
            elif node.tag=='blockLeftPadding':
                styles.append(('LEFTPADDING', start, stop, utils.unit_get(node.get('length'))))
            elif node.tag=='blockRightPadding':
                styles.append(('RIGHTPADDING', start, stop, utils.unit_get(node.get('length'))))
            elif node.tag=='blockTopPadding':
                styles.append(('TOPPADDING', start, stop, utils.unit_get(node.get('length'))))
            elif node.tag=='blockBottomPadding':
                styles.append(('BOTTOMPADDING', start, stop, utils.unit_get(node.get('length'))))
            elif node.tag=='blockBackground':
                styles.append(('BACKGROUND', start, stop, color.get(node.get('colorName'))))
            if node.get('size'):
                styles.append(('FONTSIZE', start, stop, utils.unit_get(node.get('size'))))
            elif node.tag=='lineStyle':
                kind = node.get('kind')
                kind_list = [ 'GRID', 'BOX', 'OUTLINE', 'INNERGRID', 'LINEBELOW', 'LINEABOVE','LINEBEFORE', 'LINEAFTER' ]
                assert kind in kind_list
                thick = 1
                if node.get('thickness'):
                    thick = float(node.get('thickness'))
                styles.append((kind, start, stop, thick, color.get(node.get('colorName'))))
        return platypus.tables.TableStyle(styles)

    def para_style_get(self, node):
        style = False
        sname = node.get('style')
        if sname:
            if sname in self.styles_obj:
                style = self.styles_obj[sname]
            else:
                _logger.warning('Warning: style not found, %s - setting default!\n' % (node.get('style'),) )
        if not style:
            style = self.default_style['Normal']
        para_update = self._para_style_update(node)
        if para_update:
            # update style only is necessary
            style = copy.deepcopy(style)
            style.__dict__.update(para_update)
        return style

class _rml_doc(object):
    def __init__(self, node, localcontext=None, images=None, path='.', title=None):
        if images is None:
            images = {}
        if localcontext is None:
            localcontext = {}
        self.localcontext = localcontext
        self.etree = node
        self.filename = self.etree.get('filename')
        self.images = images
        self.path = path
        self.title = title

    def docinit(self, els):
        from reportlab.lib.fonts import addMapping
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        for node in els:
            for font in node.findall('registerFont'):
                name = font.get('fontName').encode('ascii')
                fname = font.get('fontFile').encode('ascii')
                if name not in pdfmetrics._fonts:
                    pdfmetrics.registerFont(TTFont(name, fname))
                addMapping(name, 0, 0, name)    #normal
                addMapping(name, 0, 1, name)    #italic
                addMapping(name, 1, 0, name)    #bold
                addMapping(name, 1, 1, name)    #italic and bold

    def setTTFontMapping(self,face, fontname, filename, mode='all'):
        from reportlab.lib.fonts import addMapping
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        if fontname not in pdfmetrics._fonts:
            pdfmetrics.registerFont(TTFont(fontname, filename))
        if mode == 'all':
            addMapping(face, 0, 0, fontname)    #normal
            addMapping(face, 0, 1, fontname)    #italic
            addMapping(face, 1, 0, fontname)    #bold
            addMapping(face, 1, 1, fontname)    #italic and bold
        elif (mode== 'normal') or (mode == 'regular'):
            addMapping(face, 0, 0, fontname)    #normal
        elif mode == 'italic':
            addMapping(face, 0, 1, fontname)    #italic
        elif mode == 'bold':
            addMapping(face, 1, 0, fontname)    #bold
        elif mode == 'bolditalic':
            addMapping(face, 1, 1, fontname)    #italic and bold

    def _textual_image(self, node):
        rc = ''
        for n in node:
            rc +=( etree.tostring(n) or '') + n.tail
        return base64.decodestring(node.tostring())

    def _images(self, el):
        result = {}
        for node in el.findall('.//image'):
            rc =( node.text or '')
            result[node.get('name')] = base64.decodestring(rc)
        return result

    def render(self, out):
        el = self.etree.findall('.//docinit')
        if el:
            self.docinit(el)

        el = self.etree.findall('.//stylesheet')
        self.styles = _rml_styles(el,self.localcontext)

        el = self.etree.findall('.//images')
        if el:
            self.images.update( self._images(el[0]) )

        el = self.etree.findall('.//template')
        if len(el):
            pt_obj = _rml_template(self.localcontext, out, el[0], self, images=self.images, path=self.path, title=self.title)
            el = utils._child_get(self.etree, self, 'story')
            pt_obj.render(el)
        else:
            self.canvas = canvas.Canvas(out)
            pd = self.etree.find('pageDrawing')[0]
            pd_obj = _rml_canvas(self.canvas, self.localcontext, None, self, self.images, path=self.path, title=self.title)
            pd_obj.render(pd)

            self.canvas.showPage()
            self.canvas.save()

class _rml_canvas(object):
    def __init__(self, canvas, localcontext, doc_tmpl=None, doc=None, images=None, path='.', title=None):
        if images is None:
            images = {}
        self.localcontext = localcontext
        self.canvas = canvas
        self.styles = doc.styles
        self.doc_tmpl = doc_tmpl
        self.doc = doc
        self.images = images
        self.path = path
        self.title = title
        if self.title:
            self.canvas.setTitle(self.title)

    def _textual(self, node, x=0, y=0):
        text = node.text and node.text.encode('utf-8') or ''
        rc = utils._process_text(self, text)
        for n in node:
            if n.tag == 'seq':
                from reportlab.lib.sequencer import getSequencer
                seq = getSequencer()
                rc += str(seq.next(n.get('id')))
            if n.tag == 'pageCount':
                if x or y:
                    self.canvas.translate(x,y)
                self.canvas.doForm('pageCount%s' % (self.canvas._storyCount,))
                if x or y:
                    self.canvas.translate(-x,-y)
            if n.tag == 'pageNumber':
                rc += str(self.canvas.getPageNumber())
            rc += utils._process_text(self, n.tail)
        return rc.replace('\n','')

    def _drawString(self, node):
        v = utils.attr_get(node, ['x','y'])
        text=self._textual(node, **v)
        text = utils.xml2str(text)
        self.canvas.drawString(text=text, **v)

    def _drawCenteredString(self, node):
        v = utils.attr_get(node, ['x','y'])
        text=self._textual(node, **v)
        text = utils.xml2str(text)
        self.canvas.drawCentredString(text=text, **v)

    def _drawRightString(self, node):
        v = utils.attr_get(node, ['x','y'])
        text=self._textual(node, **v)
        text = utils.xml2str(text)
        self.canvas.drawRightString(text=text, **v)

    def _rect(self, node):
        if node.get('round'):
            self.canvas.roundRect(radius=utils.unit_get(node.get('round')), **utils.attr_get(node, ['x','y','width','height'], {'fill':'bool','stroke':'bool'}))
        else:
            self.canvas.rect(**utils.attr_get(node, ['x','y','width','height'], {'fill':'bool','stroke':'bool'}))

    def _ellipse(self, node):
        x1 = utils.unit_get(node.get('x'))
        x2 = utils.unit_get(node.get('width'))
        y1 = utils.unit_get(node.get('y'))
        y2 = utils.unit_get(node.get('height'))

        self.canvas.ellipse(x1,y1,x2,y2, **utils.attr_get(node, [], {'fill':'bool','stroke':'bool'}))

    def _curves(self, node):
        line_str = node.text.split()
        lines = []
        while len(line_str)>7:
            self.canvas.bezier(*[utils.unit_get(l) for l in line_str[0:8]])
            line_str = line_str[8:]

    def _lines(self, node):
        line_str = node.text.split()
        lines = []
        while len(line_str)>3:
            lines.append([utils.unit_get(l) for l in line_str[0:4]])
            line_str = line_str[4:]
        self.canvas.lines(lines)

    def _grid(self, node):
        xlist = [utils.unit_get(s) for s in node.get('xs').split(',')]
        ylist = [utils.unit_get(s) for s in node.get('ys').split(',')]

        self.canvas.grid(xlist, ylist)

    def _translate(self, node):
        dx = utils.unit_get(node.get('dx')) or 0
        dy = utils.unit_get(node.get('dy')) or 0
        self.canvas.translate(dx,dy)

    def _circle(self, node):
        self.canvas.circle(x_cen=utils.unit_get(node.get('x')), y_cen=utils.unit_get(node.get('y')), r=utils.unit_get(node.get('radius')), **utils.attr_get(node, [], {'fill':'bool','stroke':'bool'}))

    def _place(self, node):
        flows = _rml_flowable(self.doc, self.localcontext, images=self.images, path=self.path, title=self.title).render(node)
        infos = utils.attr_get(node, ['x','y','width','height'])

        infos['y']+=infos['height']
        for flow in flows:
            w,h = flow.wrap(infos['width'], infos['height'])
            if w<=infos['width'] and h<=infos['height']:
                infos['y']-=h
                flow.drawOn(self.canvas,infos['x'],infos['y'])
                infos['height']-=h
            else:
                raise ValueError("Not enough space")

    def _line_mode(self, node):
        ljoin = {'round':1, 'mitered':0, 'bevelled':2}
        lcap = {'default':0, 'round':1, 'square':2}

        if node.get('width'):
            self.canvas.setLineWidth(utils.unit_get(node.get('width')))
        if node.get('join'):
            self.canvas.setLineJoin(ljoin[node.get('join')])
        if node.get('cap'):
            self.canvas.setLineCap(lcap[node.get('cap')])
        if node.get('miterLimit'):
            self.canvas.setDash(utils.unit_get(node.get('miterLimit')))
        if node.get('dash'):
            dashes = node.get('dash').split(',')
            for x in range(len(dashes)):
                dashes[x]=utils.unit_get(dashes[x])
            self.canvas.setDash(node.get('dash').split(','))

    def _image(self, node):
        import urllib
        import urlparse
        from reportlab.lib.utils import ImageReader
        nfile = node.get('file')
        if not nfile:
            if node.get('name'):
                image_data = self.images[node.get('name')]
                _logger.debug("Image %s used", node.get('name'))
                s = StringIO(image_data)
            else:
                newtext = node.text
                if self.localcontext:
                    res = utils._regex.findall(newtext)
                    for key in res:
                        newtext = eval(key, {}, self.localcontext) or ''
                image_data = None
                if newtext:
                    image_data = base64.decodestring(newtext)
                if image_data:
                    s = StringIO(image_data)
                else:
                    _logger.debug("No image data!")
                    return False
        else:
            if nfile in self.images:
                s = StringIO(self.images[nfile])
            else:
                try:
                    up = urlparse.urlparse(str(nfile))
                except ValueError:
                    up = False
                if up and up.scheme:
                    # RFC: do we really want to open external URLs?
                    # Are we safe from cross-site scripting or attacks?
                    _logger.debug("Retrieve image from %s", nfile)
                    u = urllib.urlopen(str(nfile))
                    s = StringIO(u.read())
                else:
                    _logger.debug("Open image file %s ", nfile)
                    s = _open_image(nfile, path=self.path)
        try:
            img = ImageReader(s)
            (sx,sy) = img.getSize()
            _logger.debug("Image is %dx%d", sx, sy)
            args = { 'x': 0.0, 'y': 0.0, 'mask': 'auto'}
            for tag in ('width','height','x','y'):
                if node.get(tag):
                    args[tag] = utils.unit_get(node.get(tag))
            if ('width' in args) and (not 'height' in args):
                args['height'] = sy * args['width'] / sx
            elif ('height' in args) and (not 'width' in args):
                args['width'] = sx * args['height'] / sy
            elif ('width' in args) and ('height' in args):
                if (float(args['width'])/args['height'])>(float(sx)>sy):
                    args['width'] = sx * args['height'] / sy
                else:
                    args['height'] = sy * args['width'] / sx
            self.canvas.drawImage(img, **args)
        finally:
            s.close()
#        self.canvas._doc.SaveToFile(self.canvas._filename, self.canvas)

    def _path(self, node):
        self.path = self.canvas.beginPath()
        self.path.moveTo(**utils.attr_get(node, ['x','y']))
        for n in utils._child_get(node, self):
            if not n.text :
                if n.tag=='moveto':
                    vals = utils.text_get(n).split()
                    self.path.moveTo(utils.unit_get(vals[0]), utils.unit_get(vals[1]))
                elif n.tag=='curvesto':
                    vals = utils.text_get(n).split()
                    while len(vals)>5:
                        pos=[]
                        while len(pos)<6:
                            pos.append(utils.unit_get(vals.pop(0)))
                        self.path.curveTo(*pos)
            elif n.text:
                data = n.text.split()               # Not sure if I must merge all TEXT_NODE ?
                while len(data)>1:
                    x = utils.unit_get(data.pop(0))
                    y = utils.unit_get(data.pop(0))
                    self.path.lineTo(x,y)
        if (not node.get('close')) or utils.bool_get(node.get('close')):
            self.path.close()
        self.canvas.drawPath(self.path, **utils.attr_get(node, [], {'fill':'bool','stroke':'bool'}))

    def setFont(self, node):
        fontname = node.get('name')
        if fontname not in pdfmetrics.getRegisteredFontNames()\
             or fontname not in pdfmetrics.standardFonts:
                # let reportlab attempt to find it
                try:
                    pdfmetrics.getFont(fontname)
                except Exception:
                    _logger.debug('Could not locate font %s, substituting default: %s',
                                 fontname,
                                 self.canvas._fontname)
                    fontname = self.canvas._fontname
        return self.canvas.setFont(fontname, utils.unit_get(node.get('size')))

    def render(self, node):
        tags = {
            'drawCentredString': self._drawCenteredString,
            'drawRightString': self._drawRightString,
            'drawString': self._drawString,
            'rect': self._rect,
            'ellipse': self._ellipse,
            'lines': self._lines,
            'grid': self._grid,
            'curves': self._curves,
            'fill': lambda node: self.canvas.setFillColor(color.get(node.get('color'))),
            'stroke': lambda node: self.canvas.setStrokeColor(color.get(node.get('color'))),
            'setFont': self.setFont ,
            'place': self._place,
            'circle': self._circle,
            'lineMode': self._line_mode,
            'path': self._path,
            'rotate': lambda node: self.canvas.rotate(float(node.get('degrees'))),
            'translate': self._translate,
            'image': self._image
        }
        for n in utils._child_get(node, self):
            if n.tag in tags:
                tags[n.tag](n)

class _rml_draw(object):
    def __init__(self, localcontext, node, styles, images=None, path='.', title=None):
        if images is None:
            images = {}
        self.localcontext = localcontext
        self.node = node
        self.styles = styles
        self.canvas = None
        self.images = images
        self.path = path
        self.canvas_title = title

    def render(self, canvas, doc):
        canvas.saveState()
        cnv = _rml_canvas(canvas, self.localcontext, doc, self.styles, images=self.images, path=self.path, title=self.canvas_title)
        cnv.render(self.node)
        canvas.restoreState()

class _rml_Illustration(platypus.flowables.Flowable):
    def __init__(self, node, localcontext, styles, self2):
        self.localcontext = (localcontext or {}).copy()
        self.node = node
        self.styles = styles
        self.width = utils.unit_get(node.get('width'))
        self.height = utils.unit_get(node.get('height'))
        self.self2 = self2
    def wrap(self, *args):
        return self.width, self.height
    def draw(self):
        drw = _rml_draw(self.localcontext ,self.node,self.styles, images=self.self2.images, path=self.self2.path, title=self.self2.title)
        drw.render(self.canv, None)

class _rml_flowable(object):
    def __init__(self, doc, localcontext, images=None, path='.', title=None):
        if images is None:
            images = {}
        self.localcontext = localcontext
        self.doc = doc
        self.styles = doc.styles
        self.images = images
        self.path = path
        self.title = title

    def _textual(self, node):
        rc1 = utils._process_text(self, node.text or '')
        for n in utils._child_get(node,self):
            txt_n = copy.deepcopy(n)
            for key in txt_n.attrib.keys():
                if key in ('rml_except', 'rml_loop', 'rml_tag'):
                    del txt_n.attrib[key]
            if not n.tag == 'bullet':
                txt_n.text = utils.xml2str(self._textual(n))
            txt_n.tail = n.tail and utils.xml2str(utils._process_text(self, n.tail.replace('\n',''))) or ''
            rc1 += etree.tostring(txt_n)
        return rc1

    def _table(self, node):
        children = utils._child_get(node,self,'tr')
        if not children:
            return None
        length = 0
        colwidths = None
        rowheights = None
        data = []
        styles = []
        posy = 0
        for tr in children:
            paraStyle = None
            if tr.get('style'):
                st = copy.deepcopy(self.styles.table_styles[tr.get('style')])
                for si in range(len(st._cmds)):
                    s = list(st._cmds[si])
                    s[1] = (s[1][0],posy)
                    s[2] = (s[2][0],posy)
                    st._cmds[si] = tuple(s)
                styles.append(st)
            if tr.get('paraStyle'):
                paraStyle = self.styles.styles[tr.get('paraStyle')]
            data2 = []
            posx = 0
            for td in utils._child_get(tr, self,'td'):
                if td.get('style'):
                    st = copy.deepcopy(self.styles.table_styles[td.get('style')])
                    for s in st._cmds:
                        s[1][1] = posy
                        s[2][1] = posy
                        s[1][0] = posx
                        s[2][0] = posx
                    styles.append(st)
                if td.get('paraStyle'):
                    # TODO: merge styles
                    paraStyle = self.styles.styles[td.get('paraStyle')]
                posx += 1

                flow = []
                for n in utils._child_get(td, self):
                    if n.tag == etree.Comment:
                        n.text = ''
                        continue
                    fl = self._flowable(n, extra_style=paraStyle)
                    if isinstance(fl,list):
                        flow  += fl
                    else:
                        flow.append( fl )

                if not len(flow):
                    flow = self._textual(td)
                data2.append( flow )
            if len(data2)>length:
                length=len(data2)
                for ab in data:
                    while len(ab)<length:
                        ab.append('')
            while len(data2)<length:
                data2.append('')
            data.append( data2 )
            posy += 1

        if node.get('colWidths'):
            assert length == len(node.get('colWidths').split(','))
            colwidths = [utils.unit_get(f.strip()) for f in node.get('colWidths').split(',')]
        if node.get('rowHeights'):
            rowheights = [utils.unit_get(f.strip()) for f in node.get('rowHeights').split(',')]
            if len(rowheights) == 1:
                rowheights = rowheights[0]
        table = platypus.LongTable(data = data, colWidths=colwidths, rowHeights=rowheights, **(utils.attr_get(node, ['splitByRow'] ,{'repeatRows':'int','repeatCols':'int'})))
        if node.get('style'):
            table.setStyle(self.styles.table_styles[node.get('style')])
        for s in styles:
            table.setStyle(s)
        return table

    def _illustration(self, node):
        return _rml_Illustration(node, self.localcontext, self.styles, self)

    def _textual_image(self, node):
        return base64.decodestring(node.text)

    def _pto(self, node):
        sub_story = []
        pto_header = None
        pto_trailer = None
        for node in utils._child_get(node, self):
            if node.tag == etree.Comment:
                node.text = ''
                continue
            elif node.tag=='pto_header':
                pto_header = self.render(node)
            elif node.tag=='pto_trailer':
                pto_trailer = self.render(node)
            else:
                flow = self._flowable(node)
                if flow:
                    if isinstance(flow,list):
                        sub_story = sub_story + flow
                    else:
                        sub_story.append(flow)
        return platypus.flowables.PTOContainer(sub_story, trailer=pto_trailer, header=pto_header)

    def _flowable(self, node, extra_style=None):
        if node.tag=='pto':
            return self._pto(node)
        if node.tag=='para':
            style = self.styles.para_style_get(node)
            if extra_style:
                style.__dict__.update(extra_style)
            result = []
            for i in self._textual(node).split('\n'):
                result.append(platypus.Paragraph(i, style, **(utils.attr_get(node, [], {'bulletText':'str'}))))
            return result
        elif node.tag=='barCode':
            try:
                from reportlab.graphics.barcode import code128
                from reportlab.graphics.barcode import code39
                from reportlab.graphics.barcode import code93
                from reportlab.graphics.barcode import common
                from reportlab.graphics.barcode import fourstate
                from reportlab.graphics.barcode import usps
                from reportlab.graphics.barcode import createBarcodeDrawing

            except ImportError:
                _logger.warning("Cannot use barcode renderers:", exc_info=True)
                return None
            args = utils.attr_get(node, [], {'ratio':'float','xdim':'unit','height':'unit','checksum':'int','quiet':'int','width':'unit','stop':'bool','bearers':'int','barWidth':'float','barHeight':'float'})
            codes = {
                'codabar': lambda x: common.Codabar(x, **args),
                'code11': lambda x: common.Code11(x, **args),
                'code128': lambda x: code128.Code128(str(x), **args),
                'standard39': lambda x: code39.Standard39(str(x), **args),
                'standard93': lambda x: code93.Standard93(str(x), **args),
                'i2of5': lambda x: common.I2of5(x, **args),
                'extended39': lambda x: code39.Extended39(str(x), **args),
                'extended93': lambda x: code93.Extended93(str(x), **args),
                'msi': lambda x: common.MSI(x, **args),
                'fim': lambda x: usps.FIM(x, **args),
                'postnet': lambda x: usps.POSTNET(x, **args),
                'ean13': lambda x: createBarcodeDrawing('EAN13', value=str(x), **args),
                'qrcode': lambda x: createBarcodeDrawing('QR', value=x, **args),
            }
            code = 'code128'
            if node.get('code'):
                code = node.get('code').lower()
            return codes[code](self._textual(node))
        elif node.tag=='name':
            self.styles.names[ node.get('id')] = node.get('value')
            return None
        elif node.tag=='xpre':
            style = self.styles.para_style_get(node)
            return platypus.XPreformatted(self._textual(node), style, **(utils.attr_get(node, [], {'bulletText':'str','dedent':'int','frags':'int'})))
        elif node.tag=='pre':
            style = self.styles.para_style_get(node)
            return platypus.Preformatted(self._textual(node), style, **(utils.attr_get(node, [], {'bulletText':'str','dedent':'int'})))
        elif node.tag=='illustration':
            return  self._illustration(node)
        elif node.tag=='blockTable':
            return  self._table(node)
        elif node.tag=='title':
            styles = reportlab.lib.styles.getSampleStyleSheet()
            style = styles['Title']
            return platypus.Paragraph(self._textual(node), style, **(utils.attr_get(node, [], {'bulletText':'str'})))
        elif re.match('^h([1-9]+[0-9]*)$', (node.tag or '')):
            styles = reportlab.lib.styles.getSampleStyleSheet()
            style = styles['Heading'+str(node.tag[1:])]
            return platypus.Paragraph(self._textual(node), style, **(utils.attr_get(node, [], {'bulletText':'str'})))
        elif node.tag=='image':
            image_data = False
            if not node.get('file'):
                if node.get('name'):
                    if node.get('name') in self.doc.images:
                        _logger.debug("Image %s read ", node.get('name'))
                        image_data = self.doc.images[node.get('name')].read()
                    else:
                        _logger.warning("Image %s not defined", node.get('name'))
                        return False
                else:
                    import base64
                    newtext = node.text
                    if self.localcontext:
                        newtext = utils._process_text(self, node.text or '')
                    image_data = base64.decodestring(newtext)
                if not image_data:
                    _logger.debug("No inline image data")
                    return False
                image = StringIO(image_data)
            else:
                _logger.debug("Image get from file %s", node.get('file'))
                image = _open_image(node.get('file'), path=self.doc.path)
            return platypus.Image(image, mask=(250,255,250,255,250,255), **(utils.attr_get(node, ['width','height'])))
        elif node.tag=='spacer':
            if node.get('width'):
                width = utils.unit_get(node.get('width'))
            else:
                width = utils.unit_get('1cm')
            length = utils.unit_get(node.get('length'))
            return platypus.Spacer(width=width, height=length)
        elif node.tag=='section':
            return self.render(node)
        elif node.tag == 'pageNumberReset':
            return PageReset()
        elif node.tag in ('pageBreak', 'nextPage'):
            return platypus.PageBreak()
        elif node.tag=='condPageBreak':
            return platypus.CondPageBreak(**(utils.attr_get(node, ['height'])))
        elif node.tag=='setNextTemplate':
            return platypus.NextPageTemplate(str(node.get('name')))
        elif node.tag=='nextFrame':
            return platypus.CondPageBreak(1000)           # TODO: change the 1000 !
        elif node.tag == 'setNextFrame':
            from reportlab.platypus.doctemplate import NextFrameFlowable
            return NextFrameFlowable(str(node.get('name')))
        elif node.tag == 'currentFrame':
            from reportlab.platypus.doctemplate import CurrentFrameFlowable
            return CurrentFrameFlowable(str(node.get('name')))
        elif node.tag == 'frameEnd':
            return EndFrameFlowable()
        elif node.tag == 'hr':
            width_hr=node.get('width') or '100%'
            color_hr=node.get('color')  or 'black'
            thickness_hr=node.get('thickness') or 1
            lineCap_hr=node.get('lineCap') or 'round'
            return platypus.flowables.HRFlowable(width=width_hr,color=color.get(color_hr),thickness=float(thickness_hr),lineCap=str(lineCap_hr))
        else:
            sys.stderr.write('Warning: flowable not yet implemented: %s !\n' % (node.tag,))
            return None

    def render(self, node_story):
        def process_story(node_story):
            sub_story = []
            for node in utils._child_get(node_story, self):
                if node.tag == etree.Comment:
                    node.text = ''
                    continue
                flow = self._flowable(node)
                if flow:
                    if isinstance(flow,list):
                        sub_story = sub_story + flow
                    else:
                        sub_story.append(flow)
            return sub_story
        return process_story(node_story)


class EndFrameFlowable(ActionFlowable):
    def __init__(self,resume=0):
        ActionFlowable.__init__(self,('frameEnd',resume))

class TinyDocTemplate(platypus.BaseDocTemplate):

    def beforeDocument(self):
        # Store some useful value directly inside canvas, so it's available
        # on flowable drawing (needed for proper PageCount handling)
        self.canv._doPageReset = False
        self.canv._storyCount = 0

    def ___handle_pageBegin(self):
        self.page += 1
        self.pageTemplate.beforeDrawPage(self.canv,self)
        self.pageTemplate.checkPageSize(self.canv,self)
        self.pageTemplate.onPage(self.canv,self)
        for f in self.pageTemplate.frames: f._reset()
        self.beforePage()
        self._curPageFlowableCount = 0
        if hasattr(self,'_nextFrameIndex'):
            del self._nextFrameIndex
        for f in self.pageTemplate.frames:
            if f.id == 'first':
                self.frame = f
                break
        self.handle_frameBegin()

    def afterPage(self):
        if self.canv._doPageReset:
            # Following a <pageReset/> tag:
            # - we reset page number to 0
            # - we add  an new PageCount flowable (relative to the current
            #   story number), but not for NumeredCanvas at is handle page
            #   count itself)
            # NOTE: _rml_template render() method add a PageReset flowable at end
            #   of each story, so we're sure to pass here at least once per story.
            if not isinstance(self.canv, NumberedCanvas):
                self.handle_flowable([ PageCount(story_count=self.canv._storyCount) ])
            self.canv._pageCount = self.page
            self.page = 0
            self.canv._flag = True
            self.canv._pageNumber = 0
            self.canv._doPageReset = False
            self.canv._storyCount += 1

class _rml_template(object):
    def __init__(self, localcontext, out, node, doc, images=None, path='.', title=None):
        if images is None:
            images = {}
        if not localcontext:
            localcontext={'internal_header':True}
        self.localcontext = localcontext
        self.images= images
        self.path = path
        self.title = title

        pagesize_map = {'a4': A4,
                    'us_letter': letter
                    }
        pageSize = (841.8897637795275, 595.275590551181)
        self.doc_tmpl = TinyDocTemplate(out, pagesize=pageSize, **utils.attr_get(node, ['leftMargin','rightMargin','topMargin','bottomMargin'], {'allowSplitting':'int','showBoundary':'bool','rotation':'int','title':'str','author':'str'}))
        self.page_templates = []
        self.styles = doc.styles
        self.doc = doc
        self.image=[]
        pts = node.findall('pageTemplate')
        for pt in pts:
            frames = []
            for frame_el in pt.findall('frame'):
                frame = platypus.Frame( **(utils.attr_get(frame_el, ['x1','y1', 'width','height', 'leftPadding', 'rightPadding', 'bottomPadding', 'topPadding'], {'id':'str', 'showBoundary':'bool'})) )
                if utils.attr_get(frame_el, ['last']):
                    frame.lastFrame = True
                frames.append( frame )
            try :
                gr = pt.findall('pageGraphics')\
                    or pt[1].findall('pageGraphics')
            except Exception: # FIXME: be even more specific, perhaps?
                gr=''
            if len(gr):
#                self.image=[ n for n in utils._child_get(gr[0], self) if n.tag=='image' or not self.localcontext]
                drw = _rml_draw(self.localcontext,gr[0], self.doc, images=images, path=self.path, title=self.title)
                self.page_templates.append( platypus.PageTemplate(frames=frames, onPage=drw.render, **utils.attr_get(pt, [], {'id':'str'}) ))
            else:
                drw = _rml_draw(self.localcontext,node,self.doc,title=self.title)
                self.page_templates.append( platypus.PageTemplate(frames=frames,onPage=drw.render, **utils.attr_get(pt, [], {'id':'str'}) ))
        self.doc_tmpl.addPageTemplates(self.page_templates)

    def render(self, node_stories):
        if self.localcontext and not self.localcontext.get('internal_header',False):
            del self.localcontext['internal_header']
        fis = []
        r = _rml_flowable(self.doc,self.localcontext, images=self.images, path=self.path, title=self.title)
        story_cnt = 0
        for node_story in node_stories:
            if story_cnt > 0:
                fis.append(platypus.PageBreak())
            fis += r.render(node_story)
            # Reset Page Number with new story tag
            fis.append(PageReset())
            story_cnt += 1
        if self.localcontext and self.localcontext.get('internal_header',False):
            self.doc_tmpl.afterFlowable(fis)
            self.doc_tmpl.build(fis,canvasmaker=NumberedCanvas)
        else:
            self.doc_tmpl.build(fis)

def parseNode(rml, localcontext=None, fout=None, images=None, path='.', title=None):
    node = etree.XML(rml)
    r = _rml_doc(node, localcontext, images, path, title=title)
    #try to override some font mappings
    try:
        from customfonts import SetCustomFonts
        SetCustomFonts(r)
    except ImportError:
        # means there is no custom fonts mapping in this system.
        pass
    except Exception:
        _logger.warning('Cannot set font mapping', exc_info=True)
        pass
    fp = StringIO()
    r.render(fp)
    return fp.getvalue()

def parseString(rml, localcontext=None, fout=None, images=None, path='.', title=None):
    node = etree.XML(rml)
    r = _rml_doc(node, localcontext, images, path, title=title)

    #try to override some font mappings
    try:
        from customfonts import SetCustomFonts
        SetCustomFonts(r)
    except Exception:
        pass

    if fout:
        fp = file(fout,'wb')
        r.render(fp)
        fp.close()
        return fout
    else:
        fp = StringIO()
        r.render(fp)
        return fp.getvalue()

def trml2pdf_help():
    print 'Usage: trml2pdf input.rml >output.pdf'
    print 'Render the standard input (RML) and output a PDF file'
    sys.exit(0)

if __name__=="__main__":
    if len(sys.argv)>1:
        if sys.argv[1]=='--help':
            trml2pdf_help()
        print parseString(file(sys.argv[1], 'r').read()),
    else:
        print 'Usage: trml2pdf input.rml >output.pdf'
        print 'Try \'trml2pdf --help\' for more information.'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: