# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_vn_default_invoice_symbol_id = fields.Many2one(
        related='company_id.l10n_vn_symbol_id',
        string='Default Symbol',
        domain="[('company_id', '=', company_id), ('usage', '=', 'invoice')]",
        groups='base.group_system',
        help='This symbol will be used on invoices by default.',
        readonly=False,
    )
