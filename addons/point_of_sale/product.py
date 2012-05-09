#!/usr/bin/env python
from osv import osv, fields

class product_category(osv.osv):
    _inherit = 'product.category'

    _columns = {
        'to_weight' : fields.boolean('To Weight'),
    }

    _defaults = {
        'to_weight' : False,
    }
