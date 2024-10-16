# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.addons import point_of_sale


class PosOrder(point_of_sale.PosOrder):

    # referenced in l10n_id/models/res_bank.py where we will link QRIS transactions
    # to the record that initiates the payment flow
    l10n_id_qris_transaction_ids = fields.Many2many('l10n_id.qris.transaction')
