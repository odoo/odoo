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

from osv import fields
from osv import osv
from tools import config

import base64
class base_openoffice(osv.osv_memory):
    _name = "base.openoffice"
    _description = "Open Office Report Desinger"
    _columns = {
                'base_desinger_url': fields.char('Documentation URL', size=300, readonly=True),
                'plugin_file':fields.binary('OpenOffice Report Desinger',readonly=True),
                'pdf_file':fields.binary('Documenation', size=64 ,readonly=True),                
    }
    def add_plugin(self, cr, uid, ids, context):
        data = {}
        file = open(config['addons_path'] + "/base_report_designer/report_desinger/openoffice_report_designer/openerp_report_designer.zip", 'r')
        data['plugin_file'] = base64.encodestring(file.read())
        self.write(cr, uid, ids, data)
        return False
            
    def process_pdf_file(self, cr, uid, ids, context):
        """
        Default Attach  Plug-in Installation File.
        """
        data = {}
        pdf_file = open(config['addons_path'] + "/base_report_designer/report_desinger/doc/OpenOffice.pdf", 'r')
        data['pdf_file'] = base64.encodestring(pdf_file.read())
        self.write(cr, uid, ids, data)
        return False    
    _defaults = {
        'name' : 'tiny_plugin-2.0.xpi',
        'pdf_name' : 'Installation Guide to OpenOffice Report Desinger.pdf',
        'base_desinger_url':'http://doc.openerp.com/developer/7_23_RAD_tools/index.html#open-office-report-designer'
        
        }
        
base_openoffice()