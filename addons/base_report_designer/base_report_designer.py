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

from osv import osv
from openerp_sxw2rml import sxw2rml
from StringIO import StringIO
import base64
import pooler
import addons
import sys 

class report_xml(osv.osv):
    _inherit = 'ir.actions.report.xml'

    def sxwtorml(self, cr, uid, file_sxw, file_type):
        '''
        The use of this function is to get rml file from sxw file.
        '''
        sxwval = StringIO(base64.decodestring(file_sxw))
        if file_type=='sxw':
            fp = open(addons.get_module_resource('base_report_designer','openerp_sxw2rml', 'normalized_oo2rml.xsl'),'rb')
        if file_type=='odt':
            fp = open(addons.get_module_resource('base_report_designer','openerp_sxw2rml', 'normalized_odt2rml.xsl'),'rb')
        return  {'report_rml_content': str(sxw2rml(sxwval, xsl=fp.read()))}

    def upload_report(self, cr, uid, report_id, file_sxw, file_type, context=None):
        '''
        Untested function
        '''
        pool = pooler.get_pool(cr.dbname)
        sxwval = StringIO(base64.decodestring(file_sxw))
        if file_type=='sxw':
            fp = open(addons.get_module_resource('base_report_designer','openerp_sxw2rml', 'normalized_oo2rml.xsl'),'rb')
        if file_type=='odt':
            fp = open(addons.get_module_resource('base_report_designer','openerp_sxw2rml', 'normalized_odt2rml.xsl'),'rb')
        report = pool.get('ir.actions.report.xml').write(cr, uid, [report_id], {
            'report_sxw_content': base64.decodestring(file_sxw), 
            'report_rml_content': str(sxw2rml(sxwval, xsl=fp.read())), 
        })
        pool.get('ir.actions.report.xml').register_all(cr)
        return True

    def report_get(self, cr, uid, report_id, context=None):
        report = self.browse(cr, uid, report_id, context=context)
        reload(sys) 
        sys.setdefaultencoding( "latin-1" )    
        return {
            'file_type' : report.report_type, 
            'report_sxw_content': report.report_sxw_content and base64.encodestring(report.report_sxw_content) or False, 
            'report_rml_content': report.report_rml_content and base64.encodestring(report.report_rml_content) or False
        }

report_xml()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

