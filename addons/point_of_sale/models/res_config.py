from openerp.osv import fields, osv

class pos_configuration(osv.TransientModel):
    _inherit = 'base.config.settings'
    _name = 'pos.config.settings'

    _columns = {
        'module_pos_restaurant': fields.boolean("Use restaurant extensions",
            help='This module adds several restaurant features to the Point of Sale: \n\n- Bill Printing: Allows you to print a receipt before the order is paid \n\n- Bill Splitting: Allows you to split an order into different orders \n\n- Kitchen Order Printing: allows you to print orders updates to kitchen or bar printers'),
        'module_pos_loyalty': fields.boolean("Use loyalty programs",
            help='Allows you to define a loyalty program in the point of sale, where the customers earn loyalty points and get rewards'),
        'module_pos_discount': fields.boolean("Allow global discounts on point of sale orders",
            help='Allows the cashier to quickly give a percentage sale discount for all the sales order to a customer'),
    }
