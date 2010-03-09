# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Base',
    'version': '1.1',
    'category': 'Generic Modules/Base',
    'description': """The kernel of OpenERP, needed for all installation.""",
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': [],
    'init_xml': [
        'base_data.xml',
        'base_menu.xml',
        'security/base_security.xml',
        'res/res_security.xml',
        'maintenance/maintenance_security.xml'
    ],
    'update_xml': [
        'base_update.xml',
        'ir/wizard/wizard_menu_view.xml',
        'ir/ir.xml',
        'ir/workflow/workflow_view.xml',
        'module/module_wizard.xml',
        'module/module_view.xml',
        'module/module_data.xml',
        'module/module_report.xml',
        'res/res_request_view.xml',
        'res/res_lang_view.xml',
        'res/partner/partner_report.xml',
        'res/partner/partner_view.xml',
        'res/partner/partner_wizard.xml',
        'res/bank_view.xml',
        'res/country_view.xml',
        'res/res_currency_view.xml',
        'res/partner/crm_view.xml',
        'res/partner/partner_data.xml',
        'res/ir_property_view.xml',
        'security/base_security.xml',
        'maintenance/maintenance_view.xml',
        'security/ir.model.access.csv'
    ],
    'demo_xml': [
        'base_demo.xml', 
        'res/partner/partner_demo.xml', 
        'res/partner/crm_demo.xml',
        'base_test.xml'
    ],
    'installable': True,
    'active': True,
    'certificate': '0076807797149',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
