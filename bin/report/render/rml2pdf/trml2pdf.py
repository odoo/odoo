# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
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
#    along with this program.  If not, see <http://www.gnu.org/lic    enses/>.
#
##############################################################################


import sys
from StringIO import StringIO
import copy
import reportlab
import re
from reportlab.pdfgen import canvas
from reportlab import platypus
import cStringIO
import utils
import color
import os
from lxml import etree
import base64
from reportlab.platypus.doctemplate import ActionFlowable
from tools.safe_eval import safe_eval as eval

encoding = 'utf-8'

class PageCount(platypus.Flowable):
    def draw(self):
        self.canv.beginForm("pageCount")
        self.canv.setFont("Helvetica", utils.unit_get(str(8)))
        self.canv.drawString(0, 0, str(self.canv.getPageNumber()))
        self.canv.endForm()

class PageReset(platypus.Flowable):
    def draw(self):
        self.canv._pageNumber = 0

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
                sys.stderr.write('Warning: style not found, %s - setting default!\n' % (node.get('style'),) )
        if not style:
            style = self.default_style['Normal']
        para_update = self._para_style_update(node)
        if para_update:
            # update style only is necessary
            style = copy.deepcopy(style)
            style.__dict__.update(para_update)
        return style

class _rml_doc(object):
    def __init__(self, node, localcontext, images={}, path='.', title=None):
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
                pdfmetrics.registerFont(TTFont(name, fname ))
                addMapping(name, 0, 0, name)    #normal
                addMapping(name, 0, 1, name)    #italic
                addMapping(name, 1, 0, name)    #bold
                addMapping(name, 1, 1, name)    #italic and bold

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
    def __init__(self, canvas, localcontext, doc_tmpl=None, doc=None, images={}, path='.', title=None):
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
                self.canvas.doForm('pageCount')
                if x or y:
                    self.canvas.translate(-x,-y)
            if n.tag == 'pageNumber':
                rc += str(self.canvas.getPageNumber())
            rc += utils._process_text(self, n.tail)
        return rc

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
                raise ValueError, "Not enough space"

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
        from reportlab.lib.utils import ImageReader
        if not node.get('file') :
            if node.get('name'):
                image_data = self.images[node.get('name')]
                s = cStringIO.StringIO(image_data)
            else:
                import base64
                if self.localcontext:
                   res = utils._regex.findall(node.text)
                   for key in res:
                       newtext = eval(key, {}, self.localcontext)
                       node.text = newtext
                image_data = base64.decodestring(node.text)
                if not image_data: return False
                s = cStringIO.StringIO(image_data)
        else:
            if node.get('file') in self.images:
                s = cStringIO.StringIO(self.images[node.get('file')])
            else:
                try:
                    u = urllib.urlopen(str(node.get('file')))
                    s = cStringIO.StringIO(u.read())
                except:
                    u = file(os.path.join(self.path,str(node.get('file'))), 'rb')
                    s = cStringIO.StringIO(u.read())
        img = ImageReader(s)
        (sx,sy) = img.getSize()

        args = {}
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
            'setFont': lambda node: self.canvas.setFont(node.get('name'), utils.unit_get(node.get('size'))),
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
    def __init__(self, localcontext ,node, styles, images={}, path='.', title=None):
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

class _rml_flowable(object):
    def __init__(self, doc, localcontext, images={}, path='.', title=None):
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
            if True or not self._textual(n).isspace():
                if not n.tag == 'bullet':
                    txt_n.text = utils.xml2str(self._textual(n))
                txt_n.tail = n.tail and utils._process_text(self, n.tail.replace('\n','')) or ''
                rc1 += etree.tostring(txt_n)
        return rc1

    def _table(self, node):
        childs = utils._child_get(node,self,'tr')
        if not childs:
            return None
        length = 0
        colwidths = None
        rowheights = None
        data = []
        styles = []
        posy = 0
        for tr in childs:
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
        class Illustration(platypus.flowables.Flowable):
            def __init__(self, node, localcontext, styles, self2):
                self.localcontext = localcontext.copy()
                self.node = node
                self.styles = styles
                self.width = utils.unit_get(node.get('width'))
                self.height = utils.unit_get(node.get('height'))
                self.self2 = self2
            def wrap(self, *args):
                return (self.width, self.height)
            def draw(self):
                canvas = self.canv
                drw = _rml_draw(self.localcontext ,self.node,self.styles, images=self.self2.images, path=self.self2.path, title=self.self2.title)
                drw.render(self.canv, None)
        return Illustration(node, self.localcontext, self.styles, self)

    def _textual_image(self, node):
        return base64.decodestring(node.text)

    def _flowable(self, node, extra_style=None):
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
            except Exception, e:
                return None
            args = utils.attr_get(node, [], {'ratio':'float','xdim':'unit','height':'unit','checksum':'int','quiet':'int','width':'unit','stop':'bool','bearers':'int','barWidth':'float','barHeight':'float'})
            codes = {
                'codabar': lambda x: common.Codabar(x, **args),
                'code11': lambda x: common.Code11(x, **args),
                'code128': lambda x: code128.Code128(x, **args),
                'standard39': lambda x: code39.Standard39(x, **args),
                'standard93': lambda x: code93.Standard93(x, **args),
                'i2of5': lambda x: common.I2of5(x, **args),
                'extended39': lambda x: code39.Extended39(x, **args),
                'extended93': lambda x: code93.Extended93(x, **args),
                'msi': lambda x: common.MSI(x, **args),
                'fim': lambda x: usps.FIM(x, **args),
                'postnet': lambda x: usps.POSTNET(x, **args),
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
        elif re.match('^h([1-9]+[0-9]*)$', (node.text or '')):
            styles = reportlab.lib.styles.getSampleStyleSheet()
            style = styles['Heading'+str(node.get[1:])]
            return platypus.Paragraph(self._textual(node), style, **(utils.attr_get(node, [], {'bulletText':'str'})))
        elif node.tag=='image':
            if not node.get('file'):
                if node.get('name'):
                    image_data = self.doc.images[node.get('name')].read()
                else:
                    import base64
                    if self.localcontext:
                        newtext = utils._process_text(self, node.text or '')
                        node.text = newtext
                    image_data = base64.decodestring(node.text)
                if not image_data: return False
                image = cStringIO.StringIO(image_data)
                return platypus.Image(image, mask=(250,255,250,255,250,255), **(utils.attr_get(node, ['width','height'])))
            else:
                return platypus.Image(node.get('file'), mask=(250,255,250,255,250,255), **(utils.attr_get(node, ['width','height'])))
            from reportlab.lib.utils import ImageReader
            name = str(node.get('file'))
            img = ImageReader(name)
            (sx,sy) = img.getSize()
            args = {}
            for tag in ('width','height'):
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
            return platypus.Image(name, mask=(250,255,250,255,250,255), **args)
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
    def ___handle_pageBegin(self):
        self.page = self.page + 1
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
    def afterFlowable(self, flowable):
        if isinstance(flowable, PageReset):
            self.canv._pageNumber = 0

class _rml_template(object):
    def __init__(self, localcontext, out, node, doc, images={}, path='.', title=None):
        self.localcontext = localcontext
        self.images= images
        self.path = path
        self.title = title
        if not node.get('pageSize'):
            pageSize = (utils.unit_get('21cm'), utils.unit_get('29.7cm'))
        else:
            ps = map(lambda x:x.strip(), node.get('pageSize').replace(')', '').replace('(', '').split(','))
            pageSize = ( utils.unit_get(ps[0]),utils.unit_get(ps[1]) )

        self.doc_tmpl = TinyDocTemplate(out, pagesize=pageSize, **utils.attr_get(node, ['leftMargin','rightMargin','topMargin','bottomMargin'], {'allowSplitting':'int','showBoundary':'bool','title':'str','author':'str'}))
        self.page_templates = []
        self.styles = doc.styles
        self.doc = doc
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
            except :
                gr=''
            if len(gr):
                drw = _rml_draw(self.localcontext,gr[0], self.doc, images=images, path=self.path, title=self.title)
                self.page_templates.append( platypus.PageTemplate(frames=frames, onPage=drw.render, **utils.attr_get(pt, [], {'id':'str'}) ))
            else:
                drw = _rml_draw(self.localcontext,node,self.doc,title=self.title)
                self.page_templates.append( platypus.PageTemplate(frames=frames,onPage=drw.render, **utils.attr_get(pt, [], {'id':'str'}) ))
        self.doc_tmpl.addPageTemplates(self.page_templates)

    def render(self, node_stories):
        fis = []
        r = _rml_flowable(self.doc,self.localcontext, images=self.images, path=self.path, title=self.title)
        story_cnt = 0
        for node_story in node_stories:
            if story_cnt > 0:
                fis.append(platypus.PageBreak())
            fis += r.render(node_story)
            story_cnt += 1
        if self.localcontext:
            fis.append(PageCount())
        self.doc_tmpl.build(fis)

def parseNode(rml, localcontext = {},fout=None, images={}, path='.',title=None):
    node = etree.XML(rml)
    r = _rml_doc(node, localcontext, images, path, title=title)
    fp = cStringIO.StringIO()
    r.render(fp)
    return fp.getvalue()

def parseString(rml, localcontext = {},fout=None, images={}, path='.',title=None):
    node = etree.XML(rml)
    r = _rml_doc(node, localcontext, images, path, title=title)
    if fout:
        fp = file(fout,'wb')
        r.render(fp)
        fp.close()
        return fout
    else:
        fp = cStringIO.StringIO()
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

