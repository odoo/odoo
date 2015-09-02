# -*- coding: utf-8 -*-
from openerp.osv import fields, osv


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
