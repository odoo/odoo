# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    l10n_mx_edi_payment_method_id = fields.Many2one(
        comodel_name='l10n_mx_edi.payment.method',
        string="Payment Way",
        readonly=False, store=True,
        compute='_compute_l10n_mx_edi_payment_method_id',
        help="Indicates the way the payment was/will be received, where the options could be: "
             "Cash, Nominal Check, Credit Card, etc.")

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _get_line_batch_key(self, line):
        # OVERRIDE
        # Group moves also using these additional fields.
        res = super()._get_line_batch_key(line)
        res['l10n_mx_edi_payment_method_id'] = line.move_id.l10n_mx_edi_payment_method_id.id
        return res

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('journal_id')
    def _compute_l10n_mx_edi_payment_method_id(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                batches = wizard._get_batches()
                wizard.l10n_mx_edi_payment_method_id = batches[0]['payment_values']['l10n_mx_edi_payment_method_id']
            else:
                wizard.l10n_mx_edi_payment_method_id = False

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _create_payment_vals_from_wizard(self, batch_result):
        # OVERRIDE
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals['l10n_mx_edi_payment_method_id'] = self.l10n_mx_edi_payment_method_id.id
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        # OVERRIDE
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        payment_vals['l10n_mx_edi_payment_method_id'] = batch_result['payment_values']['l10n_mx_edi_payment_method_id']
        return payment_vals
