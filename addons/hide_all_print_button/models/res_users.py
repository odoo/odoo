# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Amaya Aravind(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models


class ResUsers(models.Model):
    """Class for inherited model res.users. Contains fields that are needed
       for hiding print buttons on different models.
    """
    _inherit = 'res.users'

    hide_sale_print = fields.Boolean(string='Button in Sales',
                                     help='Enable to hide print button in '
                                          'sales for this user.')
    hide_invoicing_print = fields.Boolean(string='Button in Invoicing',
                                          help='Enable to hide print button in'
                                               ' Invoicing(Invoices and Bills)'
                                               ' for this user.')
    hide_purchase_print = fields.Boolean(string='Button in Purchase',
                                         help='Enable to hide print button in '
                                              'Purchase for this user.')
    hide_project_task_print = fields.Boolean(string='Button in Project Task',
                                             help='Enable to hide print button'
                                                  ' in Project Task for this '
                                                  'user.')
    hide_hr_employee_print = fields.Boolean(string='Button in Employee',
                                            help='Enable to hide print button '
                                                 'in Employee for this user.')
    hide_inventory_print = fields.Boolean(string='Button in Inventory',
                                          help='Enable to hide print button in'
                                               ' Inventory(Stock) for this '
                                               'user.')
    hide_stock_picking_print = fields.Boolean(string='Button in Transfers',
                                              help='Enable to hide print '
                                                   'button in Transfers '
                                                   '(Stock Picking) for this '
                                                   'user.')
    hide_stock_lot_print = fields.Boolean(
        string='Button in Lots/Serial Number',
        help='Enable to hide print button in Lots/Serial Number for '
             'this user.')
    hide_stock_quant_package_print = fields.Boolean(
        string='Button in Packages',
        help='Enable to hide print button in Packages(Stock) for this user.')
    hide_stock_location_print = fields.Boolean(
        string='Button in Stock Locations',
        help='Enable to hide print button in Stock Locations for this user.')
    hide_stock_picking_type_print = fields.Boolean(
        string='Button in Operations Types',
        help='Enable to hide print button in Operations Types for this user.')
    hide_mrp_print = fields.Boolean(
        string='Button in Manufacturing',
        help='Enable to hide print button in Manufacturing for this user.')
    hide_mrp_production_print = fields.Boolean(
        string='Button in Manufacturing Orders',
        help='Enable to hide print button in Manufacturing Orders for '
             'this user.')
    hide_mrp_bom_print = fields.Boolean(
        string='Button in Bill of Materials',
        help='Enable to hide print button in Bill of Materials for '
             'this user.')
