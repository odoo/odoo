# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountAccount(models.Model):
    _inherit = 'account.account'

    asset_model = fields.Many2one(
        'account.asset',
        domain=[('state', '=', 'model')],
        help="If this is selected, an expense/revenue will be created automatically "
             "when Journal Items on this account are posted.",
        tracking=True)
    create_asset = fields.Selection([('no', 'No'), ('draft', 'Create in draft'), ('validate', 'Create and validate')],
                                    required=True, default='no', tracking=True)
    # specify if the account can generate asset depending on it's type. It is used in the account form view
    can_create_asset = fields.Boolean(compute="_compute_can_create_asset")
    form_view_ref = fields.Char(compute='_compute_can_create_asset')
    # decimal quantities are not supported, quantities are rounded to the lower int
    multiple_assets_per_line = fields.Boolean(string='Multiple Assets per Line', default=False, tracking=True,
        help="Multiple asset items will be generated depending on the bill line quantity instead of 1 global asset.")

    @api.depends('account_type')
    def _compute_can_create_asset(self):
        for record in self:
            record.can_create_asset = record.account_type in ('asset_fixed', 'asset_non_current')
            record.form_view_ref = 'account_asset.view_account_asset_form'

    @api.onchange('create_asset')
    def _onchange_multiple_assets_per_line(self):
        for record in self:
            if record.create_asset == 'no':
                record.multiple_assets_per_line = False
