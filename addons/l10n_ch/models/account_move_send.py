from odoo import _, api, fields, models


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    l10n_ch_partners_without_street_ids = fields.One2many('res.partner', compute='_compute_l10n_ch_partners_without_street_ids')

    @api.depends('move_ids.partner_id.street', 'move_ids.partner_id.street2')
    def _compute_l10n_ch_partners_without_street_ids(self):
        for wizard in self:
            wizard.l10n_ch_partners_without_street_ids = wizard.move_ids.filtered(lambda move: (
                move.company_id.account_fiscal_country_id.code == 'CH'
                and move.partner_id.country_id.code in ('CH', 'LI')
                and not move.partner_id.street and not move.partner_id.street2
            )).partner_id

    def action_view_l10n_ch_partners_without_street_ids(self):
        self.ensure_one()
        return self.l10n_ch_partners_without_street_ids._get_records_action(name=_("Check Partner(s)"))
