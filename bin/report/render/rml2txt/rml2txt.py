#!/bin/env python
# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

# Copyright (C) 2005, Fabien Pinckaers, UCL, FSA
# Copyright (C) 2008, P. Christeas
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

Font_size= 10.0

def verbose(text):
	sys.stderr.write(text+"\n");

class textbox():
	"""A box containing plain text.
	It can have an offset, in chars.
	Lines can be either text strings, or textbox'es, recursively.
	"""
	def __init__(self,x=0, y=0):
	    self.posx = x
	    self.posy = y
	    self.lines = []
	    self.curline = ''
	    self.endspace = False
	 
	def newline(self):
	    if isinstance(self.curline, textbox):
	        self.lines.extend(self.curline.renderlines())
	    else:
	    	self.lines.append(self.curline)
	    self.curline = ''
	
	def fline(self):
	    if isinstance(self.curline, textbox):
	        self.lines.extend(self.curline.renderlines())
	    elif len(self.curline):
	    	self.lines.append(self.curline)
	    self.curline = ''
	
	def appendtxt(self,txt):
	    """Append some text to the current line.
	       Mimic the HTML behaviour, where all whitespace evaluates to
	       a single space """
	    bs = es = False
	    if txt[0].isspace():
	        bs = True
	    if txt[len(txt)-1].isspace():
		es = True
	    if bs and not self.endspace:
		self.curline += " "
	    self.curline += txt.strip().replace("\n"," ").replace("\t"," ")
	    if es:
		self.curline += " "
	    self.endspace = es

	def rendertxt(self,xoffset=0):
	    result = ''
	    lineoff = ""
	    for i in range(self.posy):
		result +="\n"
	    for i in range(self.posx+xoffset):
	        lineoff+=" "
	    for l in self.lines:
	        result+= lineoff+ l +"\n"
	    return result
	
	def renderlines(self,pad=0):
	    """Returns a list of lines, from the current object
	    pad: all lines must be at least pad characters.
	    """
	    result = []
	    lineoff = ""
	    for i in range(self.posx):
	        lineoff+=" "
	    for l in self.lines:
		lpad = ""
		if pad and len(l) < pad :
			for i in range(pad - len(l)):
				lpad += " "
	        #elif pad and len(l) > pad ?
	        result.append(lineoff+ l+lpad)
	    return result
			
			
	def haplines(self,arr,offset,cc= ''):
		""" Horizontaly append lines 
		"""
		while (len(self.lines) < len(arr)):
			self.lines.append("")
		
		for i in range(len(self.lines)):
			while (len(self.lines[i]) < offset):
				self.lines[i] += " "
		for i in range(len(arr)):
			self.lines[i] += cc +arr[i] 
		

class _flowable(object):
    def __init__(self, template, doc):
        self._tags = {
            '1title': self._tag_title,
            '1spacer': self._tag_spacer,
            'para': self._tag_para,
	    'font': self._tag_font,
	    'section': self._tag_section,
            '1nextFrame': self._tag_next_frame,
            'blockTable': self._tag_table,
            '1pageBreak': self._tag_page_break,
            '1setNextTemplate': self._tag_next_template,
        }
        self.template = template
        self.doc = doc
	self.nitags = []
	self.tbox = None

    def warn_nitag(self,tag):
	if tag not in self.nitags:
		verbose("Unknown tag \"%s\", please implement it." % tag)
		self.nitags.append(tag)
	
    def _tag_page_break(self, node):
        return "\f"

    def _tag_next_template(self, node):
        return ''

    def _tag_next_frame(self, node):
        result=self.template.frame_stop()
        result+='\n'
        result+=self.template.frame_start()
        return result

    def _tag_title(self, node):
        node.tagName='h1'
        return node.toxml()

    def _tag_spacer(self, node):
        length = 1+int(utils.unit_get(node.getAttribute('length')))/35
        return "\n"*length

    def _tag_table(self, node):
	self.tb.fline()
	saved_tb = self.tb
	self.tb = None
	sizes = None
        if node.hasAttribute('colWidths'):
            sizes = map(lambda x: utils.unit_get(x), node.getAttribute('colWidths').split(','))
	trs = []
	for n in node.childNodes:
	    if n.nodeType == node.ELEMENT_NODE and n.localName == 'tr':
		tds = []
		for m in n.childNodes:
		    if m.nodeType == node.ELEMENT_NODE and m.localName == 'td':
		        self.tb = textbox()
			self.rec_render_cnodes(m)
			tds.append(self.tb)
			self.tb = None
		if len(tds):
		    trs.append(tds)
	
	if not sizes:
		verbose("computing table sizes..")
	for tds in trs:
		trt = textbox()
		off=0
		for i in range(len(tds)):
			p = int(sizes[i]/Font_size)
			trl = tds[i].renderlines(pad=p)
			trt.haplines(trl,off)
			off += sizes[i]/Font_size
		saved_tb.curline = trt
		saved_tb.fline()
	
	self.tb = saved_tb
        return

    def _tag_para(self, node):
	#TODO: styles
	self.rec_render_cnodes(node)
	self.tb.newline()

    def _tag_section(self, node):
	#TODO: styles
	self.rec_render_cnodes(node)
	self.tb.newline()

    def _tag_font(self, node):
	"""We do ignore fonts.."""
	self.rec_render_cnodes(node)

    def rec_render_cnodes(self,node):
	for n in node.childNodes:
	    self.rec_render(n)

    def rec_render(self,node):
        """ Recursive render: fill outarr with text of current node
	"""
	if node.nodeType == node.TEXT_NODE:
		self.tb.appendtxt(node.data)
	elif node.nodeType==node.ELEMENT_NODE:
		if node.localName in self._tags:
		    self._tags[node.localName](node)
		else:
		    self.warn_nitag(node.localName)
	else:
		verbose("Unknown nodeType: %d" % node.nodeType)

    def render(self, node):
	self.tb= textbox()
        #result = self.template.start()
        #result += self.template.frame_start()
	self.rec_render_cnodes(node)
        #result += self.template.frame_stop()
        #result += self.template.end()
	result = self.tb.rendertxt()
	del self.tb
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
	return "frame start"
        return '<table border="0" width="%d"><tr><td width="%d">&nbsp;</td><td>' % (self.width+self.posx,self.posx)
    def tag_end(self):
        return True
    def tag_stop(self):
	return "frame stop"
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
	return "draw string \"%s\" @(%d,%d)..\n" %("txt",self.posx,self.posy)
        self.pos.sort()
        res = '\\table ...'
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
        res+='\\table end'
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
	return "draw lines..\n"
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
        return ''

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
	return "template end\n"
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
        template = _rml_template(self.dom.documentElement.getElementsByTagName('template')[0])
        f = _flowable(template, self.dom)
        self.result += f.render(self.dom.documentElement.getElementsByTagName('story')[0])
        del f
        self.result += '\n'
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
    print 'Usage: rml2txt input.rml >output.html'
    print 'Render the standard input (RML) and output an TXT file'
    sys.exit(0)

if __name__=="__main__":
    if len(sys.argv)>1:
        if sys.argv[1]=='--help':
            trml2pdf_help()
        print parseString(file(sys.argv[1], 'r').read()).encode('iso8859-7')
    else:
        print 'Usage: trml2txt input.rml >output.pdf'
        print 'Try \'trml2txt --help\' for more information.'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

