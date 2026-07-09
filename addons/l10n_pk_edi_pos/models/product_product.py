from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    l10n_pk_is_fbr_3rd_schedule = fields.Boolean(related='product_tmpl_id.l10n_pk_is_fbr_3rd_schedule')
