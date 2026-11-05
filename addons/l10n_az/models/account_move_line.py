from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_az_eqf_product_code = fields.Char(
        string="National Goods/Services Code",
        compute='_compute_l10n_az_eqf_product_code',
        store=True,
        readonly=False,
        precompute=True,
        copy=False,
        help="10-digit code of the national goods and services classification, reported on the electronic invoice (EQF).",
    )

    @api.depends('product_id', 'product_id.l10n_az_eqf_product_code')
    def _compute_l10n_az_eqf_product_code(self):
        for line in self:
            if line.move_id.country_code == 'AZ' and line.parent_state == 'draft':
                line.l10n_az_eqf_product_code = line.product_id.l10n_az_eqf_product_code
