# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_vn_edi_username = fields.Char(
        string='SInvoice Username',
        groups='base.group_system',
    )
    l10n_vn_edi_password = fields.Char(
        string='Sinvoice Password',
        groups='base.group_system',
    )
    l10n_vn_edi_token = fields.Char(
        string='Sinvoice Access Token',
        groups='base.group_system',
        readonly=True,
    )
    l10n_vn_edi_token_expiry = fields.Datetime(
        string='Sinvoice Access Token Expiration Date',
        groups='base.group_system',
        readonly=True,
    )
