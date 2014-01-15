
from openerp.osv import osv, fields

class sale_configuration(osv.osv_memory):
    _inherit = 'sale.config.settings'

    _columns = {
        'group_product_characteristics': fields.boolean("Support multiple characteristics per products  ",
            implied_group='product.group_product_characteristics',
            help="""Allow to manage several characteristics per product. This characteristics are used for filter and compare your products. As an example, if you  sell all in one computers, you may have characteristics like RAM, Processor Speed, Manufacturing, to compare products"""),
    }
