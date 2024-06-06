from odoo import fields, models, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_pl_vat_b_spv = fields.Boolean(
        string='B_SPV',
        help="Transfer of a single-purpose voucher effected by a taxable person acting on his/its own behalf",
    )
    l10n_pl_vat_b_spv_dostawa = fields.Boolean(
        string='B_SPV_Dostawa',
        help="Supply of goods and/or services covered by a single-purpose voucher to a taxpayer",
    )
    l10n_pl_vat_b_mpv_prowizja = fields.Boolean(
        string='B_MPV_Prowizja',
        help="Supply of agency and other services pertaining to the transfer of a single-purpose voucher",
    )

    def action_post(self):
        "Validation to avoid having credit notes with more than the invoice"
        for record in self:
            if record.company_id.account_fiscal_country_id.code == 'PL' and record.reversed_entry_id and\
                record.reversed_entry_id.amount_total < record.amount_total and record.move_type != 'entry':
                raise ValidationError(_("Credit notes can't have a total amount greater than the invoice's"))
        return super().action_post()
