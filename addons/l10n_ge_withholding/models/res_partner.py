from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_ge_wht_category_ids = fields.Many2many(
        comodel_name='l10n_ge.wht.category',
        string="Withholding Tax Categories",
        help="Income recipient categories the contact falls under. They narrow the withholding taxes"
        " offered on its bills and payments.",
    )

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ["l10n_ge_wht_category_ids"]
