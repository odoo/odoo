# -*- encoding: utf-8 -*-
from openerp import models, fields, api, _


class product_template(models.Model):
    _inherit = ['product.template']

    @api.model
    def _get_product_template_type(self):
        res = super(product_template, self)._get_product_template_type()
        if 'digital' not in [item[0] for item in res]:
            res.append(('digital', 'Digital Content'))
        return res
