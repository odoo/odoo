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

import base64
from StringIO import StringIO

from openerp.modules.module import get_module_resource
import openerp.modules.registry
from openerp.osv import osv
from openerp_sxw2rml import sxw2rml


class report_xml(osv.osv):
    _inherit = 'ir.actions.report.xml'

    def sxwtorml(self, cr, uid, file_sxw, file_type):
        '''
        The use of this function is to get rml file from sxw file.
        '''
        sxwval = StringIO(base64.decodestring(file_sxw))
        if file_type=='sxw':
            fp = open(get_module_resource('base_report_designer','openerp_sxw2rml', 'normalized_oo2rml.xsl'),'rb')
        if file_type=='odt':
            fp = open(get_module_resource('base_report_designer','openerp_sxw2rml', 'normalized_odt2rml.xsl'),'rb')
        return  {'report_rml_content': str(sxw2rml(sxwval, xsl=fp.read()))}

    def upload_report(self, cr, uid, report_id, file_sxw, file_type, context=None):
        '''
        Untested function
        '''
        sxwval = StringIO(base64.decodestring(file_sxw))
        if file_type=='sxw':
            fp = open(get_module_resource('base_report_designer','openerp_sxw2rml', 'normalized_oo2rml.xsl'),'rb')
        if file_type=='odt':
            fp = open(get_module_resource('base_report_designer','openerp_sxw2rml', 'normalized_odt2rml.xsl'),'rb')
        report = self.pool['ir.actions.report.xml'].write(cr, uid, [report_id], {
            'report_sxw_content': base64.decodestring(file_sxw), 
            'report_rml_content': str(sxw2rml(sxwval, xsl=fp.read())), 
        })

        return True

    def report_get(self, cr, uid, report_id, context=None):
        # skip osv.fields.sanitize_binary_value() because we want the raw bytes in all cases
        context = dict(context or {}, bin_raw=True)
        report = self.browse(cr, uid, report_id, context=context)
        sxw_data = report.report_sxw_content
        rml_data = report.report_rml_content
        if isinstance(sxw_data, unicode):
            sxw_data = sxw_data.encode("iso-8859-1", "replace")
        if isinstance(rml_data, unicode):
            rml_data = rml_data.encode("iso-8859-1", "replace")
        return {
            'file_type' : report.report_type,
            'report_sxw_content': sxw_data and base64.encodestring(sxw_data) or False,
            'report_rml_content': rml_data and base64.encodestring(rml_data) or False
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

