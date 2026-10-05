# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_vn_default_invoice_symbol_id = fields.Many2one(
        related='company_id.l10n_vn_symbol_id',
        ui_domain="[('company_id', '=', company_id), ('usage', '=', 'invoice')]",
        string='Default Symbol',
        groups='base.group_system',
        help='This symbol will be used on invoices by default.',
        readonly=False,
    )
    module_l10n_vn_edi_viettel = fields.Boolean(string="Vietnam E-invoicing (SInvoice)")

    def action_l10n_vn_activate_edi_viettel(self):
        """ Install the SInvoice (Viettel) e-invoicing module and reload the settings page to show its settings. """
        # _get() returns a sudo record: drop it so button_immediate_install checks the user is an admin
        module = self.env['ir.module.module']._get('l10n_vn_edi_viettel').sudo(False)
        if module:
            self._install_modules(module)
        return {'type': 'ir.actions.client', 'tag': 'reload'}
