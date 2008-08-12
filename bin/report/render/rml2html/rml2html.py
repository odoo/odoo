# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 Tiny SPRL (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
###############################################################################
#!/usr/bin/python

# Copyright (C) 2005, Fabien Pinckaers, UCL, FSA
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys
import StringIO
import xml.dom.minidom
import copy

import utils

class _flowable(object):
    def __init__(self, template, doc):
        self._tags = {
            'title': self._tag_title,
            'spacer': self._tag_spacer,
            'para': self._tag_para,
            'nextFrame': self._tag_next_frame,
            'blockTable': self._tag_table,
            'pageBreak': self._tag_page_break,
            'setNextTemplate': self._tag_next_template,
        }
        self.template = template
        self.doc = doc

    def _tag_page_break(self, node):
        return '<br/>'*3

    def _tag_next_template(self, node):
        return ''

    def _tag_next_frame(self, node):
        result=self.template.frame_stop()
        result+='<br/>'
        result+=self.template.frame_start()
        return result

    def _tag_title(self, node):
        node.tagName='h1'
        return node.toxml()

    def _tag_spacer(self, node):
        length = 1+int(utils.unit_get(node.getAttribute('length')))/35
        return "<br/>"*length

    def _tag_table(self, node):
        node.tagName='table'
        if node.hasAttribute('colWidths'):
            sizes = map(lambda x: utils.unit_get(x), node.getAttribute('colWidths').split(','))
            tr = self.doc.createElement('tr')
            for s in sizes:
                td = self.doc.createElement('td')
                td.setAttribute("width", str(s))
                tr.appendChild(td)
            node.appendChild(tr)
        return node.toxml()

    def _tag_para(self, node):
        node.tagName='p'
        if node.hasAttribute('style'):
            node.setAttribute('class', node.getAttribute('style'))
        return node.toxml()

    def render(self, node):
        result = self.template.start()
        result += self.template.frame_start()
        for n in node.childNodes:
            if n.nodeType==node.ELEMENT_NODE:
                if n.localName in self._tags:
                    result += self._tags[n.localName](n)
                else:
                    pass
                    #print 'tag', n.localName, 'not yet implemented!'
        result += self.template.frame_stop()
        result += self.template.end()
        return result

class _rml_tmpl_tag(object):
    def __init__(self, *args):
        pass
    def tag_start(self):
        return ''
    def tag_end(self):
        return False
    def tag_stop(self):
        return ''
    def tag_mergeable(self):
        return True

class _rml_tmpl_frame(_rml_tmpl_tag):
    def __init__(self, posx, width):
        self.width = width
        self.posx = posx
    def tag_start(self):
        return '<table border="0" width="%d"><tr><td width="%d">&nbsp;</td><td>' % (self.width+self.posx,self.posx)
    def tag_end(self):
        return True
    def tag_stop(self):
        return '</td></tr></table><br/>'
    def tag_mergeable(self):
        return False

    # An awfull workaround since I don't really understand the semantic behind merge.
    def merge(self, frame):
        pass

class _rml_tmpl_draw_string(_rml_tmpl_tag):
    def __init__(self, node, style):
        self.posx = utils.unit_get(node.getAttribute('x'))
        self.posy =  utils.unit_get(node.getAttribute('y'))
        aligns = {
            'drawString': 'left',
            'drawRightString': 'right',
            'drawCentredString': 'center'
        }
        align = aligns[node.localName]
        self.pos = [(self.posx, self.posy, align, utils.text_get(node), style.get('td'), style.font_size_get('td'))]

    def tag_start(self):
        self.pos.sort()
        res = '<table border="0" cellpadding="0" cellspacing="0"><tr>'
        posx = 0
        i = 0
        for (x,y,align,txt, style, fs) in self.pos:
            if align=="left":
                pos2 = len(txt)*fs
                res+='<td width="%d"></td><td style="%s" width="%d">%s</td>' % (x - posx, style, pos2, txt)
                posx = x+pos2
            if align=="right":
                res+='<td width="%d" align="right" style="%s">%s</td>' % (x - posx, style, txt)
                posx = x
            if align=="center":
                res+='<td width="%d" align="center" style="%s">%s</td>' % ((x - posx)*2, style, txt)
                posx = 2*x-posx
            i+=1
        res+='</tr></table>'
        return res
    def merge(self, ds):
        self.pos+=ds.pos

class _rml_tmpl_draw_lines(_rml_tmpl_tag):
    def __init__(self, node, style):
        coord = [utils.unit_get(x) for x in utils.text_get(node).split(' ')]
        self.ok = False
        self.posx = coord[0]
        self.posy = coord[1]
        self.width = coord[2]-coord[0]
        self.ok = coord[1]==coord[3]
        self.style = style
        self.style = style.get('hr')

    def tag_start(self):
        if self.ok:
            return '<table border="0" cellpadding="0" cellspacing="0" width="%d"><tr><td width="%d"></td><td><hr width="100%%" style="margin:0px; %s"></td></tr></table>' % (self.posx+self.width,self.posx,self.style)
        else:
            return ''

class _rml_stylesheet(object):
    def __init__(self, stylesheet, doc):
        self.doc = doc
        self.attrs = {}
        self._tags = {
            'fontSize': lambda x: ('font-size',str(utils.unit_get(x))+'px'),
            'alignment': lambda x: ('text-align',str(x))
        }
        result = ''
        for ps in stylesheet.getElementsByTagName('paraStyle'):
            attr = {}
            attrs = ps.attributes
            for i in range(attrs.length):
                 name = attrs.item(i).localName
                 attr[name] = ps.getAttribute(name)
            attrs = []
            for a in attr:
                if a in self._tags:
                    attrs.append("%s:%s" % self._tags[a](attr[a]))
            if len(attrs):
                result += "p."+attr['name']+" {"+'; '.join(attrs)+"}\n"
        self.result = result

    def render(self):
        return self.result

class _rml_draw_style(object):
    def __init__(self):
        self.style = {}
        self._styles = {
            'fill': lambda x: {'td': {'color':x.getAttribute('color')}},
            'setFont': lambda x: {'td': {'font-size':x.getAttribute('size')+'px'}},
            'stroke': lambda x: {'hr': {'color':x.getAttribute('color')}},
        }
    def update(self, node):
        if node.localName in self._styles:
            result = self._styles[node.localName](node)
            for key in result:
                if key in self.style:
                    self.style[key].update(result[key])
                else:
                    self.style[key] = result[key]
    def font_size_get(self,tag):
        size  = utils.unit_get(self.style.get('td', {}).get('font-size','16'))
        return size

    def get(self,tag):
        if not tag in self.style:
            return ""
        return ';'.join(['%s:%s' % (x[0],x[1]) for x in self.style[tag].items()])

class _rml_template(object):
    def __init__(self, template):
        self.frame_pos = -1
        self.frames = []
        self.template_order = []
        self.page_template = {}
        self.loop = 0
        self._tags = {
            'drawString': _rml_tmpl_draw_string,
            'drawRightString': _rml_tmpl_draw_string,
            'drawCentredString': _rml_tmpl_draw_string,
            'lines': _rml_tmpl_draw_lines
        }
        self.style = _rml_draw_style()
        for pt in template.getElementsByTagName('pageTemplate'):
            frames = {}
            id = pt.getAttribute('id')
            self.template_order.append(id)
            for tmpl in pt.getElementsByTagName('frame'):
                posy = int(utils.unit_get(tmpl.getAttribute('y1'))) #+utils.unit_get(tmpl.getAttribute('height')))
                posx = int(utils.unit_get(tmpl.getAttribute('x1')))
                frames[(posy,posx,tmpl.getAttribute('id'))] = _rml_tmpl_frame(posx, utils.unit_get(tmpl.getAttribute('width')))
            for tmpl in template.getElementsByTagName('pageGraphics'):
                for n in tmpl.childNodes:
                    if n.nodeType==n.ELEMENT_NODE:
                        if n.localName in self._tags:
                            t = self._tags[n.localName](n, self.style)
                            frames[(t.posy,t.posx,n.localName)] = t
                        else:
                            self.style.update(n)
            keys = frames.keys()
            keys.sort()
            keys.reverse()
            self.page_template[id] = []
            for key in range(len(keys)):
                if key>0 and keys[key-1][0] == keys[key][0]:
                    if type(self.page_template[id][-1]) == type(frames[keys[key]]):
                        if self.page_template[id][-1].tag_mergeable():
                            self.page_template[id][-1].merge(frames[keys[key]])
                        continue
                self.page_template[id].append(frames[keys[key]])
        self.template = self.template_order[0]

    def _get_style(self):
        return self.style

    def set_next_template(self):
        self.template = self.template_order[(self.template_order.index(name)+1) % self.template_order]
        self.frame_pos = -1

    def set_template(self, name):
        self.template = name
        self.frame_pos = -1

    def frame_start(self):
        result = ''
        frames = self.page_template[self.template]
        ok = True
        while ok:
            self.frame_pos += 1
            if self.frame_pos>=len(frames):
                self.frame_pos=0
                self.loop=1
                ok = False
                continue
            f = frames[self.frame_pos]
            result+=f.tag_start()
            ok = not f.tag_end()
            if ok:
                result+=f.tag_stop()
        return result

    def frame_stop(self):
        frames = self.page_template[self.template]
        f = frames[self.frame_pos]
        result=f.tag_stop()
        return result

    def start(self):
        return ''
    
    def end(self):
        result = ''
        while not self.loop:
            result += self.frame_start()
            result += self.frame_stop()
        return result

class _rml_doc(object):
    def __init__(self, data):
        self.dom = xml.dom.minidom.parseString(data)
        self.filename = self.dom.documentElement.getAttribute('filename')
        self.result = ''

    def render(self, out):
        self.result += '''<!DOCTYPE HTML PUBLIC "-//w3c//DTD HTML 4.0 Frameset//EN">
<html>
<head>
    <style type="text/css">
        p {margin:0px; font-size:12px;}
        td {font-size:14px;}
'''
        style = self.dom.documentElement.getElementsByTagName('stylesheet')[0]
        s = _rml_stylesheet(style, self.dom)
        self.result += s.render()
        self.result+='''
    </style>
</head>
<body>'''

        template = _rml_template(self.dom.documentElement.getElementsByTagName('template')[0])
        f = _flowable(template, self.dom)
        self.result += f.render(self.dom.documentElement.getElementsByTagName('story')[0])
        del f
        self.result += '</body></html>'
        out.write( self.result)

def parseString(data, fout=None):
    r = _rml_doc(data)
    if fout:
        fp = file(fout,'wb')
        r.render(fp)
        fp.close()
        return fout
    else:
        fp = StringIO.StringIO()
        r.render(fp)
        return fp.getvalue()

def trml2pdf_help():
    print 'Usage: rml2html input.rml >output.html'
    print 'Render the standard input (RML) and output an HTML file'
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

