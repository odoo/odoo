from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_ge_wht_category_ids = fields.Many2many(
        comodel_name='l10n_ge.wht.category',
        string="Withholding Tax Categories",
        help="Income recipient categories the contact falls under. They determine which withholding taxes can be selected on payments to this contact.",
    )
