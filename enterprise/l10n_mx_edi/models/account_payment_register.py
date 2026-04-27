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

    l10n_mx_edi_cfdi_origin = fields.Char(string="CFDI Origin")

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('journal_id')
    def _compute_l10n_mx_edi_payment_method_id(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                wizard.l10n_mx_edi_payment_method_id = wizard.line_ids.move_id.l10n_mx_edi_payment_method_id[:1]
            else:
                wizard.l10n_mx_edi_payment_method_id = False

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _create_payment_vals_from_wizard(self, batch_result):
        # OVERRIDE
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals['l10n_mx_edi_payment_method_id'] = self.l10n_mx_edi_payment_method_id.id
        payment_vals['l10n_mx_edi_cfdi_origin'] = self.l10n_mx_edi_cfdi_origin
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        # OVERRIDE
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        payment_vals['l10n_mx_edi_payment_method_id'] = self.l10n_mx_edi_payment_method_id.id
        payment_vals['l10n_mx_edi_cfdi_origin'] = batch_result['payment_values'].get('l10n_mx_edi_cfdi_origin')
        return payment_vals
