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

from openerp.osv import fields, osv
import openerp.report.interface
from openerp.report.report_sxw import rml_parse

from webkit_report import WebKitParser

def register_report(name, model, tmpl_path, parser=rml_parse):
    """Register the report into the services"""
    name = 'report.%s' % name
    if name in openerp.report.interface.report_int._reports:
        service = openerp.report.interface.report_int._reports[name]
        if isinstance(service, WebKitParser):
            #already instantiated properly, skip it
            return
        if hasattr(service, 'parser'):
            parser = service.parser
        del openerp.report.interface.report_int._reports[name]
    WebKitParser(name, model, tmpl_path, parser=parser)


class ReportXML(osv.osv):
    _inherit = 'ir.actions.report.xml'
    _columns = {
        'webkit_header':  fields.property(
                                            'ir.header_webkit',
                                            type='many2one',
                                            relation='ir.header_webkit',
                                            string='Webkit Header',
                                            help="The header linked to the report",
                                            view_load=True,
                                            required=True
                                        ),
        'webkit_debug' : fields.boolean('Webkit debug', help="Enable the webkit engine debugger"),
        'report_webkit_data': fields.text('Webkit Template', help="This template will be used if the main report file is not found"),
        'precise_mode':fields.boolean('Precise Mode', help='This mode allow more precise element \
                                                            position as each object is printed on a separate HTML.\
                                                            but memory and disk usage is wider')
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
