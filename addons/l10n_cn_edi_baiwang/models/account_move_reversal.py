# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

RED_FORM_TYPES = [
    ('01', '01 Billing Error (开票有误)'),
    ('02', '02 Sales Return (销货退回)'),
    ('03', '03 Service Termination (服务中止)'),
    ('04', '04 Sales Discount (销售折让)'),
]


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_cn_baiwang_red_form_type = fields.Selection(
        selection=RED_FORM_TYPES,
        string="Red Form Reason",
        help="Reason code sent to Baiwang when creating a credit note red form.",
    )
    l10n_cn_baiwang_use_red_form_reason = fields.Boolean(
        compute='_compute_l10n_cn_baiwang_use_red_form_reason',
    )

    @api.depends('move_ids', 'country_code', 'move_type')
    def _compute_l10n_cn_baiwang_use_red_form_reason(self):
        for wizard in self:
            wizard.l10n_cn_baiwang_use_red_form_reason = (
                wizard.country_code == 'CN'
                and wizard.move_type == 'out_invoice'
                and bool(wizard.move_ids)
                and bool(wizard.company_id.l10n_cn_baiwang_app_key)
            )

    @api.onchange('l10n_cn_baiwang_red_form_type')
    def _onchange_l10n_cn_baiwang_red_form_type(self):
        for wizard in self:
            if wizard.l10n_cn_baiwang_use_red_form_reason and wizard.l10n_cn_baiwang_red_form_type:
                label = dict(RED_FORM_TYPES).get(wizard.l10n_cn_baiwang_red_form_type)
                wizard.reason = (label and label[3:]) or False

    def _prepare_default_reversal(self, move):
        values = super()._prepare_default_reversal(move)
        if self.l10n_cn_baiwang_red_form_type:
            values['l10n_cn_baiwang_red_form_type'] = self.l10n_cn_baiwang_red_form_type
        return values
