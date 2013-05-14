# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) 2005, Fabien Pinckaers, UCL, FSA
# Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
##############################################################################

import sys
import cStringIO
from lxml import etree
import copy

from openerp.report.render.rml2pdf import utils

class _flowable(object):
    def __init__(self, template, doc, localcontext = None):
        self._tags = {
            'title': self._tag_title,
            'spacer': self._tag_spacer,
            'para': self._tag_para,
            'section':self._section,
            'nextFrame': self._tag_next_frame,
            'blockTable': self._tag_table,
            'pageBreak': self._tag_page_break,
            'setNextTemplate': self._tag_next_template,
        }
        self.template = template
        self.doc = doc
        self.localcontext = localcontext
        self._cache = {}

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
        node.tag='h1'
        return etree.tostring(node)

    def _tag_spacer(self, node):
        length = 1+int(utils.unit_get(node.get('length')))/35
        return "<br/>"*length

    def _tag_table(self, node):
        new_node = copy.deepcopy(node)
        for child in new_node:
            new_node.remove(child)
        new_node.tag = 'table'
        def process(node,new_node):
            for child in utils._child_get(node,self):
                new_child = copy.deepcopy(child)
                new_node.append(new_child)
                if len(child):
                    for n in new_child:
                        new_child.remove(n)
                    process(child, new_child)
                else:
                    new_child.text  = utils._process_text(self, child.text)
                    new_child.tag = 'p'
                    try:
                        if new_child.get('style').find('terp_tblheader')!= -1:
                            new_node.tag = 'th'
                    except Exception:
                        pass
        process(node,new_node)
        if new_node.get('colWidths',False):
            sizes = map(lambda x: utils.unit_get(x), new_node.get('colWidths').split(','))
            tr = etree.SubElement(new_node, 'tr')
            for s in sizes:
                etree.SubElement(tr, 'td', width=str(s))

        return etree.tostring(new_node)

    def _tag_para(self, node):
        new_node = copy.deepcopy(node)
        new_node.tag = 'p'
        if new_node.attrib.get('style',False):
            new_node.set('class', new_node.get('style'))
        new_node.text = utils._process_text(self, node.text)
        return etree.tostring(new_node)

    def _section(self, node):
        result = ''
        for child in utils._child_get(node, self):
            if child.tag in self._tags:
                result += self._tags[child.tag](child)
        return result

    def render(self, node):
        result = self.template.start()
        result += self.template.frame_start()
        for n in utils._child_get(node, self):
            if n.tag in self._tags:
                result += self._tags[n.tag](n)
            else:
                pass
        result += self.template.frame_stop()
        result += self.template.end()
        return result.encode('utf-8').replace('"',"\'").replace('°','&deg;')

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
        return "<table border=\'0\' width=\'%d\'><tr><td width=\'%d\'>&nbsp;</td><td>" % (self.width+self.posx,self.posx)
    def tag_end(self):
        return True
    def tag_stop(self):
        return '</td></tr></table><br/>'
    def tag_mergeable(self):
        return False

    def merge(self, frame):
        pass

class _rml_tmpl_draw_string(_rml_tmpl_tag):
    def __init__(self, node, style,localcontext = {}):
        self.localcontext = localcontext
        self.posx = utils.unit_get(node.get('x'))
        self.posy =  utils.unit_get(node.get('y'))

        aligns = {
            'drawString': 'left',
            'drawRightString': 'right',
            'drawCentredString': 'center'
        }
        align = aligns[node.tag]
        self.pos = [(self.posx, self.posy, align, utils._process_text(self, node.text), style.get('td'), style.font_size_get('td'))]

    def tag_start(self):
        self.pos.sort()
        res = "<table border='0' cellpadding='0' cellspacing='0'><tr>"
        posx = 0
        i = 0
        for (x,y,align,txt, style, fs) in self.pos:
            if align=="left":
                pos2 = len(txt)*fs
                res+="<td width=\'%d\'></td><td style=\'%s\' width=\'%d\'>%s</td>" % (x - posx, style, pos2, txt)
                posx = x+pos2
            if align=="right":
                res+="<td width=\'%d\' align=\'right\' style=\'%s\'>%s</td>" % (x - posx, style, txt)
                posx = x
            if align=="center":
                res+="<td width=\'%d\' align=\'center\' style=\'%s\'>%s</td>" % ((x - posx)*2, style, txt)
                posx = 2*x-posx
            i+=1
        res+='</tr></table>'
        return res
    def merge(self, ds):
        self.pos+=ds.pos

class _rml_tmpl_draw_lines(_rml_tmpl_tag):
    def __init__(self, node, style, localcontext = {}):
        self.localcontext = localcontext
        coord = [utils.unit_get(x) for x in utils._process_text(self, node.text).split(' ')]
        self.ok = False
        self.posx = coord[0]
        self.posy = coord[1]
        self.width = coord[2]-coord[0]
        self.ok = coord[1]==coord[3]
        self.style = style
        self.style = style.get('hr')

    def tag_start(self):
        if self.ok:
            return "<table border=\'0\' cellpadding=\'0\' cellspacing=\'0\' width=\'%d\'><tr><td width=\'%d\'></td><td><hr width=\'100%%\' style=\'margin:0px; %s\'></td></tr></table>" % (self.posx+self.width,self.posx,self.style)
        else:
            return ''

class _rml_stylesheet(object):
    def __init__(self, localcontext, stylesheet, doc):
        self.doc = doc
        self.localcontext = localcontext
        self.attrs = {}
        self._tags = {
            'fontSize': lambda x: ('font-size',str(utils.unit_get(x)+5.0)+'px'),
            'alignment': lambda x: ('text-align',str(x))
        }
        result = ''
        for ps in stylesheet.findall('paraStyle'):
            attr = {}
            attrs = ps.attrib
            for key, val in attrs.items():
                attr[key] = val
            attrs = []
            for a in attr:
                if a in self._tags:
                    attrs.append('%s:%s' % self._tags[a](attr[a]))
            if len(attrs):
                result += 'p.'+attr['name']+' {'+'; '.join(attrs)+'}\n'
        self.result = result

    def render(self):
        return self.result

class _rml_draw_style(object):
    def __init__(self):
        self.style = {}
        self._styles = {
            'fill': lambda x: {'td': {'color':x.get('color')}},
            'setFont': lambda x: {'td': {'font-size':x.get('size')+'px'}},
            'stroke': lambda x: {'hr': {'color':x.get('color')}},
        }
    def update(self, node):
        if node.tag in self._styles:
            result = self._styles[node.tag](node)
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
    def __init__(self, template, localcontext=None):
        self.frame_pos = -1
        self.localcontext = localcontext
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
        rc = 'data:image/png;base64,'
        self.data = ''
        for pt in template.findall('pageTemplate'):
            frames = {}
            id = pt.get('id')
            self.template_order.append(id)
            for tmpl in pt.findall('frame'):
                posy = int(utils.unit_get(tmpl.get('y1')))
                posx = int(utils.unit_get(tmpl.get('x1')))
                frames[(posy,posx,tmpl.get('id'))] = _rml_tmpl_frame(posx, utils.unit_get(tmpl.get('width')))
            for tmpl in pt.findall('pageGraphics'):
                for n in tmpl:
                    if n.tag == 'image':
                        self.data = rc + utils._process_text(self, n.text)
                    if n.tag in self._tags:
                        t = self._tags[n.tag](n, self.style,self.localcontext)
                        frames[(t.posy,t.posx,n.tag)] = t
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
    def __init__(self, data, localcontext):
        self.dom = etree.XML(data)
        self.localcontext = localcontext
        self.filename = self.dom.get('filename')
        self.result = ''

    def render(self, out):
        self.result += '''<!DOCTYPE HTML PUBLIC "-//w3c//DTD HTML 4.0 Frameset//EN">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <style type="text/css">
        p {margin:0px; font-size:12px;}
        td {font-size:14px;}
'''
        style = self.dom.findall('stylesheet')[0]
        s = _rml_stylesheet(self.localcontext, style, self.dom)
        self.result += s.render()
        self.result+='''
    </style>
'''
        list_story =[]
        for story in utils._child_get(self.dom, self, 'story'):
            template = _rml_template(self.dom.findall('template')[0], self.localcontext)
            f = _flowable(template, self.dom, localcontext = self.localcontext)
            story_text = f.render(story)
            list_story.append(story_text)
        del f
        if template.data:
            tag = '''<img src = '%s' width=80 height=72/>'''% template.data
        else:
            tag = ''
        self.result +='''
            <script type="text/javascript">

            var indexer = 0;
            var aryTest = %s ;
            function nextData()
                {
                if(indexer < aryTest.length -1)
                    {
                    indexer += 1;
                    document.getElementById("tiny_data").innerHTML=aryTest[indexer];
                    }
                }
            function prevData()
                {
                if (indexer > 0)
                    {
                    indexer -= 1;
                    document.getElementById("tiny_data").innerHTML=aryTest[indexer];
                    }
                }
        </script>
        </head>
        <body>
            %s
            <div id="tiny_data">
                %s
            </div>
            <br>
            <input type="button" value="next" onclick="nextData();">
            <input type="button" value="prev" onclick="prevData();">

        </body></html>'''%(list_story,tag,list_story[0])
        out.write( self.result)

def parseString(data,localcontext = {}, fout=None):
    r = _rml_doc(data, localcontext)
    if fout:
        fp = file(fout,'wb')
        r.render(fp)
        fp.close()
        return fout
    else:
        fp = cStringIO.StringIO()
        r.render(fp)
        return fp.getvalue()

def rml2html_help():
    print 'Usage: rml2html input.rml >output.html'
    print 'Render the standard input (RML) and output an HTML file'
    sys.exit(0)

if __name__=="__main__":
    if len(sys.argv)>1:
        if sys.argv[1]=='--help':
            rml2html_help()
        print parseString(file(sys.argv[1], 'r').read()),
    else:
        print 'Usage: rml2html input.rml >output.html'
        print 'Try \'rml2html --help\' for more information.'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
