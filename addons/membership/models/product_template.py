# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_tracking = fields.Selection(
        selection_add=[('membership', 'Membership')], ondelete={'membership': 'set default'}
    )
    grade_id = fields.Many2one('res.partner.grade')
    pricelist_id = fields.Many2one('product.pricelist', groups='product.group_product_pricelist')
