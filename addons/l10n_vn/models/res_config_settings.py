# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_vn_default_invoice_symbol_id = fields.Many2one(
        related='company_id.l10n_vn_symbol_id',
        domain="[('company_id', '=', company_id), ('usage', '=', 'invoice')]",
        string='Default Symbol',
        groups='base.group_system',
        help='This symbol will be used on invoices by default.',
        readonly=False,
    )
    module_l10n_vn_edi_viettel = fields.Boolean(string="Vietnam E-invoicing (SInvoice)")

    def action_l10n_vn_activate_edi_viettel(self):
        module = self.env['ir.module.module']._get('l10n_vn_edi_viettel')
        if module:
            self._install_modules(module)
        return {'type': 'ir.actions.client', 'tag': 'reload'}
