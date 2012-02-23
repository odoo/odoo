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
import addons

import base64

class outlook_installer(osv.osv_memory):
    _name = 'outlook.installer'
    _inherit = 'res.config.installer'

    _columns = {
        'name':fields.char('Outlook Plug-in 32bits', size=64, readonly=True, help="outlook plug-in file. Save as this file and install this plug-in in outlook."),
        'name2':fields.char('Outlook Plug-in 64bits', size=64, readonly=True, help="outlook plug-in file. Save as this file and install this plug-in in outlook."),
        'description':fields.text('Description', readonly=True)
    }

    _defaults = {
        'name' : '/plugin_outlook/static/openerp-outlook-plugin/OpenERPOutlookPluginSetup32.msi',
        'name2' : '/plugin_outlook/static/openerp-outlook-plugin/OpenERPOutlookPluginSetup64.msi',
        'description' : """
Click on icon next to the link above to download the installer either for 32 or 64 bits and execute it.

System requirements:
    1.  MS Outlook 2005 or above.
    2.  MS .Net Framework 3.5 or above.
"""
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
