##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
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
#
##############################################################################

import render
import rml2pdf
import rml2html as htmlizer

class rml(render.render):
    def __init__(self, xml, datas={}, path='.'):
        render.render.__init__(self, datas)
        self.xml = xml
        self.output_type = 'pdf'
        self.path = path

    def _render(self):
        return rml2pdf.parseString(self.xml, images=self.bin_datas, path=self.path)

class rml2html(render.render):
    def __init__(self, xml, datas={}):
        super(rml2html, self).__init__(datas)
        self.xml = xml
        self.output_type = 'html'
    
    def _render(self):
        return htmlizer.parseString(self.xml)
