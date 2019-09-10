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

import logging

import openerp
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

class restaurant_printer(osv.osv):
    _name = 'restaurant.printer'

    _columns = {
        'name' : fields.char('Printer Name', size=32, required=True, help='An internal identification of the printer'),
        'proxy_ip': fields.char('Proxy IP Address', size=32, help="The IP Address or hostname of the Printer's hardware proxy"),
        'product_categories_ids': fields.many2many('pos.category','printer_category_rel', 'printer_id','category_id',string='Printed Product Categories'),
    }

    _defaults = {
        'name' : 'Printer',
    }

class pos_config(osv.osv):
    _inherit = 'pos.config'
    _columns = {
        'iface_splitbill': fields.boolean('Bill Splitting', help='Enables Bill Splitting in the Point of Sale'),
        'iface_printbill': fields.boolean('Bill Printing', help='Allows to print the Bill before payment'),
        'printer_ids':     fields.many2many('restaurant.printer','pos_config_printer_rel', 'config_id','printer_id',string='Order Printers'),
    }
    _defaults = {
        'iface_splitbill': False,
        'iface_printbill': False,
    }
            
