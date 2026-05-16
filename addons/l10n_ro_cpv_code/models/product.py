from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    cpv_code_id = fields.Many2one(
        comodel_name='l10n_ro.cpv.code',
        string="CPV Code",
        help="Common Procurement Vocabulary, used by e-Factura",
    )
