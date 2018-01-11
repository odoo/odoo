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

from openerp.osv import fields
from openerp.osv import osv
import base64
from openerp.tools.translate import _

class base_report_designer_installer(osv.osv_memory):
    _name = 'base_report_designer.installer'
    _inherit = 'res.config.installer'

    def default_get(self, cr, uid, fields, context=None):
        data = super(base_report_designer_installer, self).default_get(cr, uid, fields, context=context)
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        data['plugin_file'] = base_url + '/base_report_designer/static/base-report-designer-plugin/openerp_report_designer.zip'
        return data

    _columns = {
        'name':fields.char('File name'),
        'plugin_file':fields.char('OpenObject Report Designer Plug-in', readonly=True, help="OpenObject Report Designer plug-in file. Save as this file and install this plug-in in OpenOffice."),
        'description':fields.text('Description', readonly=True)
    }

    _defaults = {
        'name' : 'openerp_report_designer.zip',
        'description' : """
        * Save the OpenERP Report Designer plug-­in.
        * Follow these steps to install plug-­in.
            1. Open Extension Manager window from Menu Bar of Openoffice writer, Open Tools > Extension Menu.
            2. Click on "Add" button.
            3. Select path where the openerp_report_designer.zip is located.
            4. On the completion of adding package you will get your package under 'Extension Manager' and the status of your package become 'Enabled'.
            5. Restart openoffice writer.
        * Follow the steps to configure OpenERP Report Designer plug-­in in Openoffice writer.
            1. Connect OpenERP Server from Menu bar , OpenERP Report Designer > Server parameter.
            2. Select Server url, database and provide user name and password
            3. Click "Connect".
            4. if your connection success, A message appears like 'You can start creating your report in current document.'.
        """
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

