# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_in_partner_gstin_status = fields.Selection([
            ("active", "Active"),
            ("inactive", "Inactive"),
            ("invalid", "Invalid"),
        ],
        string="GST Status",
        compute="_compute_l10n_in_partner_gstin_status_and_date",
        help='''The GSTN status color indicates how recently it was checked when it is 'Active'.\n
                - Green means it was checked within the last 30 days.
                - Orange means it was checked between 31 and 60 days.
                - Red means it was checked more than 60 days ago.'''
    )
    l10n_in_gstin_verified_date = fields.Date(compute="_compute_l10n_in_partner_gstin_status_and_date")
    l10n_in_partner_gstin_status_color = fields.Selection([
            ("green", "Green"),
            ("yellow", "Yellow"),
            ("red", "Red"),
        ],
        compute="_compute_l10n_in_partner_gstin_status_and_date",
    )

    @api.depends('partner_id')
    def _compute_l10n_in_partner_gstin_status_and_date(self):
        for move in self:
            if move.country_code == 'IN' and move.payment_state not in ['paid', 'reversed'] and move.state != 'cancel':
                move.l10n_in_partner_gstin_status = move.partner_id.l10n_in_gstin_verified_status
                move.l10n_in_gstin_verified_date = move.partner_id.l10n_in_gstin_verified_date
                move.l10n_in_partner_gstin_status_color = move.partner_id.l10n_in_gstin_status_color
            else:
                move.l10n_in_partner_gstin_status = False
                move.l10n_in_gstin_verified_date = False
                move.l10n_in_partner_gstin_status_color = False

    def l10n_in_verify_partner_gstin_status(self):
        self.ensure_one()
        return self.partner_id.get_l10n_in_gstin_verified_status()
