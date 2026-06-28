# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_vn_edi_send_transfer_note = fields.Boolean(
        string="Send Transfer Note to SInvoice",
        groups='base.group_system',
    )
    l10n_vn_edi_stock_default_sinvoice_symbol_id = fields.Many2one(
        comodel_name='l10n_vn_edi_viettel.sinvoice.symbol',
        string="Default Delivery Symbol",
        groups='base.group_system',
    )
