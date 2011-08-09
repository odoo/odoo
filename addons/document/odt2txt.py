#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

import sys, zipfile, xml.dom.minidom
import StringIO

class OpenDocumentTextFile :
    def __init__ (self, filepath) :
        zip = zipfile.ZipFile(filepath)
        self.content = xml.dom.minidom.parseString(zip.read("content.xml"))

    def toString (self) :
        """ Converts the document to a string. """
        buffer = u""
        for val in ["text:p", "text:h", "text:list"]:
            for paragraph in self.content.getElementsByTagName(val) :
                buffer += self.textToString(paragraph) + "\n"
        return buffer

    def textToString(self, element) :
        buffer = u""
        for node in element.childNodes :
            if node.nodeType == xml.dom.Node.TEXT_NODE :
                buffer += node.nodeValue
            elif node.nodeType == xml.dom.Node.ELEMENT_NODE :
                buffer += self.textToString(node)
        return buffer

if __name__ == "__main__" :
    s =StringIO.StringIO(file(sys.argv[1]).read())
    odt = OpenDocumentTextFile(s)
    print odt.toString().encode('ascii','replace')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
