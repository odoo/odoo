# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from osv import fields,osv
from wizard.tiny_sxw2rml import sxw2rml
from StringIO import StringIO
from report import interface
import base64
import pooler
import tools

class report_xml(osv.osv):
    _inherit = 'ir.actions.report.xml'

    def sxwtorml(self,cr, uid, file_sxw,file_type):
        '''
        The use of this function is to get rml file from sxw file.
        '''
        sxwval = StringIO(base64.decodestring(file_sxw))
        if file_type=='sxw':
            fp = tools.file_open('normalized_oo2rml.xsl',
                    subdir='addons/base_report_designer/wizard/tiny_sxw2rml')
        if file_type=='odt':
            fp = tools.file_open('normalized_odt2rml.xsl',
                    subdir='addons/base_report_designer/wizard/tiny_sxw2rml')
        
        return  {'report_rml_content': str(sxw2rml(sxwval, xsl=fp.read()))}

    def upload_report(self, cr, uid, report_id, file_sxw,file_type, context):
        '''
        Untested function
        '''
        pool = pooler.get_pool(cr.dbname)
        sxwval = StringIO(base64.decodestring(file_sxw))
        if file_type=='sxw':
            fp = tools.file_open('normalized_oo2rml.xsl',
                    subdir='addons/base_report_designer/wizard/tiny_sxw2rml')
        if file_type=='odt':
            fp = tools.file_open('normalized_odt2rml.xsl',
                    subdir='addons/base_report_designer/wizard/tiny_sxw2rml')
        report = pool.get('ir.actions.report.xml').write(cr, uid, [report_id], {
            'report_sxw_content': base64.decodestring(file_sxw),
            'report_rml_content': str(sxw2rml(sxwval, xsl=fp.read())),
        })
        cr.commit()
        db = pooler.get_db_only(cr.dbname)
        interface.register_all(db)
        return True
    def report_get(self, cr, uid, report_id, context={}):
        report = self.browse(cr, uid, report_id, context)
        return {
            'file_type' : report.report_type,
            'report_sxw_content': report.report_sxw_content and base64.encodestring(report.report_sxw_content) or False,
            'report_rml_content': report.report_rml_content and base64.encodestring(report.report_rml_content) or False
        }
report_xml()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

