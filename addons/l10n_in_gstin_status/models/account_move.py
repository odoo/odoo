# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_in_partner_gstin_status = fields.Boolean(
        string="GST Status",
        compute="_compute_l10n_in_partner_gstin_status_and_date",
    )
    l10n_in_show_gstin_status = fields.Boolean(compute="_compute_l10n_in_show_gstin_status")
    l10n_in_gstin_verified_date = fields.Date(compute="_compute_l10n_in_partner_gstin_status_and_date")

    @api.depends('partner_id', 'state', 'payment_state', 'l10n_in_gst_treatment')
    def _compute_l10n_in_show_gstin_status(self):
        indian_moves = self.filtered(lambda m: m.country_code == 'IN')
        (self - indian_moves).l10n_in_show_gstin_status = False
        for move in indian_moves:
            move.l10n_in_show_gstin_status = (
                move.partner_id
                and move.state == 'posted'
                and move.move_type != 'entry'
                and move.payment_state not in ['paid', 'reversed']
                and move.l10n_in_gst_treatment in ['regular', 'composition', 'special_economic_zone', 'deemed_export', 'uin_holders']
            )

    @api.depends('partner_id')
    def _compute_l10n_in_partner_gstin_status_and_date(self):
        for move in self:
            if move.country_code == 'IN' and move.payment_state not in ['paid', 'reversed'] and move.state != 'cancel':
                move.l10n_in_partner_gstin_status = move.partner_id.l10n_in_gstin_verified_status
                move.l10n_in_gstin_verified_date = move.partner_id.l10n_in_gstin_verified_date
            else:
                move.l10n_in_partner_gstin_status = False
                move.l10n_in_gstin_verified_date = False

    def l10n_in_verify_partner_gstin_status(self):
        self.ensure_one()
        return self.with_company(self.company_id).partner_id.action_l10n_in_verify_gstin_status()
