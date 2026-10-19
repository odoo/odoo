# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    # referenced in l10n_id/models/res_bank.py where we will link QRIS transactions
    # to the record that initiates the payment flow
    l10n_id_qris_transaction_ids = fields.Many2many('l10n_id.qris.transaction', groups='account.group_account_invoice')
