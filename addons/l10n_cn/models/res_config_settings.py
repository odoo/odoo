from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_cn_output_vat_offset_account_id = fields.Many2one(
        related="company_id.l10n_cn_output_vat_offset_account_id",
        readonly=False,
    )
    l10n_cn_output_vat_offset_journal_id = fields.Many2one(
        related="company_id.l10n_cn_output_vat_offset_journal_id",
        readonly=False,
    )
    l10n_cn_vat_differential_taxation = fields.Boolean(
        related='company_id.l10n_cn_vat_differential_taxation',
        readonly=False,
    )
    module_l10n_cn_edi_yunshui = fields.Boolean(string="China E-Fapiao (Aisino Yunshui)")

    def action_l10n_cn_activate_edi_yunshui(self):
        self.env['ir.module.module'].search([('name', '=', 'l10n_cn_edi_yunshui')]).button_immediate_install()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
