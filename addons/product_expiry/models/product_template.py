from openerp.osv import fields, osv

class product_product(osv.osv):
    _inherit = 'product.template'
    _columns = {
        'life_time': fields.integer('Product Life Time',
            help='When a new a Serial Number is issued, this is the number of days before the goods may become dangerous and must not be consumed.'),
        'use_time': fields.integer('Product Use Time',
            help='When a new a Serial Number is issued, this is the number of days before the goods starts deteriorating, without being dangerous yet.'),
        'removal_time': fields.integer('Product Removal Time',
            help='When a new a Serial Number is issued, this is the number of days before the goods should be removed from the stock.'),
        'alert_time': fields.integer('Product Alert Time',
            help='When a new a Serial Number is issued, this is the number of days before an alert should be notified.'),
    }
