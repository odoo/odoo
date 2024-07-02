# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.payment import utils as payment_utils


class SaleOrder(models.Model):
    _inherit = "sale.order"

    moneris_auth_tx = fields.Boolean('Moneris Tx', compute="_compute_moneris_tx", store=True)
    moneris_done_tx = fields.Boolean('Moneris Tx', compute="_compute_moneris_tx", store=True)

    @api.depends('transaction_ids', 'transaction_ids.state', 'transaction_ids.payment_id')
    def _compute_moneris_tx(self):
        for rec in self:
            rec.moneris_auth_tx, rec.moneris_done_tx = False, False
            moneris_auth_tx = rec.transaction_ids.filtered(lambda tx: tx.state == 'authorized' and tx.provider_code == 'moneris')
            if moneris_auth_tx: rec.moneris_auth_tx = True
            moneris_done_tx = rec.transaction_ids.filtered(lambda tx: tx.state == 'done' and tx.provider_code == 'moneris')
            if moneris_done_tx: rec.moneris_done_tx = True

    def payment_action_void(self):
        """ Void all transactions linked to this sale order. """
        payment_utils.check_rights_on_recordset(self)
        # In sudo mode because we need to be able to read on provider fields.
        moneris_tx_ids = self.transaction_ids.filtered(lambda x: x.provider_code == 'moneris')
        if moneris_tx_ids:
            moneris_tx_ids.sudo().action_void()

        auth_tx_ids = self.authorized_transaction_ids.filtered(lambda x: x.provider_code != 'moneris')
        if auth_tx_ids:
            auth_tx_ids.sudo().action_void()


class AccountMove(models.Model):
    _inherit = "account.move"

    moneris_auth_tx = fields.Boolean('Moneris Tx', compute="_compute_moneris_tx", store=True)
    moneris_done_tx = fields.Boolean('Moneris Tx', compute="_compute_moneris_tx", store=True)

    @api.depends('transaction_ids', 'transaction_ids.state', 'transaction_ids.payment_id')
    def _compute_moneris_tx(self):
        for rec in self:
            rec.moneris_auth_tx, rec.moneris_done_tx = False, False
            moneris_auth_tx = rec.transaction_ids.filtered(lambda tx: tx.state == 'authorized' and tx.provider_code == 'moneris')
            if moneris_auth_tx: rec.moneris_auth_tx = True
            moneris_done_tx = rec.transaction_ids.filtered(lambda tx: tx.state == 'done' and tx.provider_code == 'moneris')
            if moneris_done_tx: rec.moneris_done_tx = True

    def payment_action_void(self):
        """ Void all transactions linked to this invoice. """
        payment_utils.check_rights_on_recordset(self)
        # In sudo mode because we need to be able to read on provider fields.
        moneris_tx_ids = self.transaction_ids.filtered(lambda x: x.provider_code == 'moneris')
        if moneris_tx_ids:
            moneris_tx_ids.sudo().action_void()

        auth_tx_ids = self.authorized_transaction_ids.filtered(lambda x: x.provider_code != 'moneris')
        if auth_tx_ids:
            auth_tx_ids.sudo().action_void()
