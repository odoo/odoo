from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_pl_vat_b_spv = fields.Boolean(
        string='B_SPV',
        help="Transfer of a single-purpose voucher effected by a taxable person acting on his/its own behalf",
        states={'draft': [('readonly', False)]},
    )
    l10n_pl_vat_b_spv_dostawa = fields.Boolean(
        string='B_SPV_Dostawa',
        help="Supply of goods and/or services covered by a single-purpose voucher to a taxpayer",
        states={'draft': [('readonly', False)]},
    )
    l10n_pl_vat_b_mpv_prowizja = fields.Boolean(
        string='B_MPV_Prowizja',
        help="Supply of agency and other services pertaining to the transfer of a single-purpose voucher",
        states={'draft': [('readonly', False)]},
    )
    l10n_pl_delivery_date = fields.Date(
        string='PL Delivery Date',
        copy=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    l10n_pl_show_delivery_date = fields.Boolean(compute='_compute_l10n_pl_show_delivery_date')

    @api.depends('country_code', 'l10n_pl_delivery_date')
    def _compute_l10n_pl_show_delivery_date(self):
        for move in self:
            move.l10n_pl_show_delivery_date = move.l10n_pl_delivery_date and move.is_sale_document() and move.country_code == 'PL'
