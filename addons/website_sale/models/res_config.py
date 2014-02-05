
from openerp.osv import osv, fields

class sale_configuration(osv.osv_memory):
    _inherit = 'sale.config.settings'

    _columns = {
        'group_product_attributes': fields.boolean("Support custom product attributes",
            group='base.group_user,base.group_portal,base.group_public',
            implied_group='product.group_product_attributes',
            help="Lets you add multiple custom attributes on products, "
                 "usable to filter and compare them. "
                 "For example if you sell computers, you could add custom attributes such as RAM size "
                 "or CPU speed to compare your products"""),
    }
