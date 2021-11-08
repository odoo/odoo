"""Hooks for Changing Menu Web_icon"""
# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2021-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import base64

from odoo import api, SUPERUSER_ID
from odoo.modules import get_module_resource


def test_pre_init_hook(cr):
    """pre init hook"""

    env = api.Environment(cr, SUPERUSER_ID, {})
    menu_item = env['ir.ui.menu'].search([('parent_id', '=', False)])

    for menu in menu_item:
        if menu.name == 'Contacts':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Contacts.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Link Tracker':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Link Tracker.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Dashboards':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Dashboards.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Sales':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Sales.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Invoicing':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Invoicing.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Inventory':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Inventory.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Purchase':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Purchase.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Calendar':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Calendar.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'CRM':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'CRM.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Note':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Note.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Website':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Website.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Point of Sale':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Point of Sale.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Manufacturing':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Manufacturing.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Repairs':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Repairs.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Email Marketing':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Email Marketing.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'SMS Marketing':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'SMS Marketing.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Project':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Project.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Surveys':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Surveys.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Employees':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Employees.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Recruitment':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Recruitment.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Attendances':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Attendances.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Time Off':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Time Off.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Expenses':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Expenses.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Maintenance':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Maintenance.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Live Chat':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Live Chat.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Lunch':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Lunch.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Fleet':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Fleet.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Timesheets':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Timesheets.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Events':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Events.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'eLearning':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'eLearning.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Members':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Members.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})


def test_post_init_hook(cr, registry):
    """post init hook"""

    env = api.Environment(cr, SUPERUSER_ID, {})
    menu_item = env['ir.ui.menu'].search([('parent_id', '=', False)])

    for menu in menu_item:
        if menu.name == 'Contacts':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Contacts.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Link Tracker':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Link Tracker.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Dashboards':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Dashboards.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Sales':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Sales.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Invoicing':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Invoicing.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Inventory':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Inventory.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Purchase':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Purchase.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Calendar':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Calendar.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'CRM':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'CRM.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Note':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Note.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Website':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Website.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Point of Sale':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Point of Sale.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Manufacturing':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Manufacturing.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Repairs':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Repairs.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Email Marketing':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Email Marketing.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'SMS Marketing':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'SMS Marketing.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Project':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Project.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Surveys':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Surveys.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Employees':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Employees.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Recruitment':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Recruitment.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Attendances':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Attendances.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Time Off':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Time Off.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Expenses':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Expenses.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Maintenance':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Maintenance.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Live Chat':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Live Chat.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Lunch':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Lunch.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Fleet':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Fleet.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Timesheets':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Timesheets.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Events':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Events.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'eLearning':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'eLearning.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
        if menu.name == 'Members':
            img_path = get_module_resource(
                'code_backend_theme', 'static', 'src', 'img', 'icons', 'Members.png')
            menu.write({'web_icon_data': base64.b64encode(open(img_path, "rb").read())})
