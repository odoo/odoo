# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import copy
import cStringIO
import re

from reportlab.lib.utils import ImageReader

from odoo.report.render.rml2pdf import utils

_regex = re.compile('\[\[(.+?)\]\]')
utils._regex = re.compile('\[\[\s*(.+?)\s*\]\]',re.DOTALL)
class html2html(object):
    def __init__(self, html, localcontext):
        self.localcontext = localcontext
        self.etree = html
        self._node = None


    def render(self):
        def process_text(node,new_node):
            if new_node.tag in ['story','tr','section']:
                new_node.attrib.clear()
            for child in utils._child_get(node, self):
                new_child = copy.deepcopy(child)
                new_node.append(new_child)
                if len(child):
                    for n in new_child:
                        new_child.text  = utils._process_text(self, child.text)
                        new_child.tail  = utils._process_text(self, child.tail)
                        new_child.remove(n)
                    process_text(child, new_child)
                else:
                    if new_child.tag=='img' and new_child.get('name'):
                        if _regex.findall(new_child.get('name')) :
                            src =  utils._process_text(self, new_child.get('name'))
                            if src :
                                new_child.set('src','data:image/gif;base64,%s'%src)
                                output = cStringIO.StringIO(base64.decodestring(src))
                                img = ImageReader(output)
                                (width,height) = img.getSize()
                                if not new_child.get('width'):
                                    new_child.set('width',str(width))
                                if not new_child.get('height') :
                                    new_child.set('height',str(height))
                            else :
                                new_child.getparent().remove(new_child)
                    new_child.text  = utils._process_text(self, child.text)
                    new_child.tail  = utils._process_text(self, child.tail)
        self._node = copy.deepcopy(self.etree)
        for n in self._node:
            self._node.remove(n)
        process_text(self.etree, self._node)
        return self._node
        
    def url_modify(self,root):
        for n in root:
            if (n.text.find('<a ')>=0 or n.text.find('&lt;a')>=0) and n.text.find('href')>=0 and n.text.find('style')<=0 :
                node = (n.tag=='span' and n.getparent().tag=='u') and n.getparent().getparent() or ((n.tag=='span') and n.getparent()) or n
                style = node.get('color') and "style='color:%s; text-decoration: none;'"%node.get('color') or ''
                if n.text.find('&lt;a')>=0:
                    t = '&lt;a '
                else :
                    t = '<a '
                href = n.text.split(t)[-1]
                n.text = ' '.join([t,style,href])
            self.url_modify(n)
        return root

def parseString(node, localcontext = {}):
    r = html2html(node, localcontext)
    root = r.render()
    root = r.url_modify(root)
    return root
