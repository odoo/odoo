# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Camptocamp SA (http://www.camptocamp.com)
# All Right Reserved
#
# Author : Nicolas Bessi (Camptocamp)
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

from tools import convert

original_xml_import = convert.xml_import

class WebkitXMLImport(original_xml_import):
    
    # Override of xml import in order to add webkit_header tag in report tag.
    # This was done with agreement of Olivier Dony as the XML api does not offer enought flexibity
    # The solution is not meant to be long term solution
    def _tag_report(self, cr, rec, data_node=None):
        if rec.get('report_type') == 'webkit':
            header = rec.get('webkit_header')
            report_id = super(WebkitXMLImport, self)._tag_report(cr, rec, data_node)
            report_obj = self.pool.get('ir.actions.report.xml')
            if header:
                if header in ('False', '0', 'None'):
                    report_obj.write(cr, self.uid, report_id, {'webkit_header': False})
                else:
                    webkit_header_id = self.id_get(cr, header)
                    report_obj.write(cr, self.uid, report_id, {'webkit_header': webkit_header_id})
                return report_id
        else:
            return super(WebkitXMLImport, self)._tag_report(cr, rec, data_node)

convert.xml_import = WebkitXMLImport
