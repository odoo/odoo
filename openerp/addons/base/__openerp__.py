# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010 OpenERP s.a. (<http://openerp.com>).
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


{
    'name': 'Base',
    'version': '1.3',
    'category': 'Hidden',
    'description': """The kernel of OpenERP, needed for all installation.""",
    'author': 'OpenERP SA',
    'maintainer': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': [],
    'init_xml': [
        'base_data.xml',
        'security/base_security.xml',
        'base_menu.xml',
        'res/res_security.xml',
        'res/res_config.xml',
        'data/res.country.state.csv'
    ],
    'update_xml': [
        'ir/wizard/wizard_menu_view.xml',
        'ir/ir.xml',
        'ir/ir_filters.xml',
        'ir/ir_config_parameter_view.xml',
        'ir/workflow/workflow_view.xml',
        'ir/report/ir_report.xml',
        'module/module_view.xml',
        'module/module_data.xml',
        'module/module_report.xml',
        'module/wizard/base_module_import_view.xml',
        'module/wizard/base_module_update_view.xml',
        'module/wizard/base_language_install_view.xml',
        'module/wizard/base_import_language_view.xml',
        'module/wizard/base_module_upgrade_view.xml',
        'module/wizard/base_module_configuration_view.xml',
        'module/wizard/base_export_language_view.xml',
        'module/wizard/base_update_translations_view.xml',
        'res/res_company_view.xml',
        'res/res_request_view.xml',
        'res/res_lang_view.xml',
        'res/res_partner_report.xml',
        'res/res_partner_view.xml',
        'res/res_partner_shortcut_data.xml',
        'res/res_bank_view.xml',
        'res/res_country_view.xml',
        'res/res_currency_view.xml',
        'res/res_users_view.xml',
        'res/res_partner_data.xml',
        'res/ir_property_view.xml',
        'security/base_security.xml',
        'publisher_warranty/publisher_warranty_view.xml',
        'security/ir.model.access.csv',
        'security/ir.model.access-1.csv', # res.partner.address is deprecated; it is still there for backward compability only and will be removed in next version
        'res/res_widget_view.xml',
        'res/res_widget_data.xml',
        'publisher_warranty/publisher_warranty_data.xml',
    ],
    'demo_xml': [
        'base_demo.xml',
        'res/res_partner_demo.xml',
        'res/res_partner_demo.yml',
        'res/res_widget_demo.xml',
    ],
    'test': [
        'test/base_test.xml',
        'test/base_test.yml',
        'test/test_context.xml',
        'test/bug_lp541545.xml',
        'test/test_osv_expression.yml',
        'test/test_ir_rule.yml', # <-- These tests modify/add/delete ir_rules.
        # Commented because this takes some time.
        # This must be (un)commented with the corresponding import statement
        # in test/__init__.py.
        # 'test/test_ir_cron.yml', # <-- These tests perform a roolback.
    ],
    'installable': True,
    'auto_install': True,
    'certificate': '0076807797149',
    "css": [ 'static/src/css/modules.css' ],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
