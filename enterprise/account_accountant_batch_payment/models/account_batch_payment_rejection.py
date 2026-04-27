# -*- coding: utf-8 -*-
from odoo import api, fields, models, Command


class AccountBatchPaymentRejection(models.TransientModel):
    _name = 'account.batch.payment.rejection'
    _description = "Manage the payment rejection from batch payments"

    # Fields that need to be populated when opening the wizard.
    in_reconcile_payment_ids = fields.Many2many(comodel_name='account.payment')

    rejected_payment_ids = fields.Many2many(
        comodel_name='account.payment',
        compute='_compute_rejected_payment_ids',
    )
    nb_rejected_payment_ids = fields.Integer(compute='_compute_rejected_payment_ids')
    nb_batch_payment_ids = fields.Integer(compute='_compute_rejected_payment_ids')

    @api.model
    def _fetch_rejected_payment_ids(self, in_reconcile_payments):
        """ Collect the payments that have been rejected from the batches.

        :param in_reconcile_payments: The payments we attempt
        :return:
        """
        batch_ids = in_reconcile_payments.batch_payment_id.ids
        if batch_ids:
            return self.env['account.payment'].search([
                ('is_matched', '=', False),
                ('batch_payment_id', 'in', batch_ids),
                ('id', 'not in', in_reconcile_payments.ids),
            ])
        else:
            return self.env['account.payment']

    @api.depends('in_reconcile_payment_ids')
    def _compute_rejected_payment_ids(self):
        for wizard in self:
            rejected_payments = wizard._fetch_rejected_payment_ids(wizard.in_reconcile_payment_ids)
            wizard.rejected_payment_ids = [Command.set(rejected_payments.ids)]
            wizard.nb_rejected_payment_ids = len(wizard.rejected_payment_ids)
            wizard.nb_batch_payment_ids = len(rejected_payments.batch_payment_id)

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def button_cancel_payments(self):
        self.rejected_payment_ids.batch_payment_id = False
        to_unlink = self.rejected_payment_ids.move_id.filtered(lambda x: not x._get_violated_lock_dates(x.date, False))
        to_reject = self.rejected_payment_ids.move_id - to_unlink
        if to_unlink:
            to_unlink.button_draft()
            to_unlink.button_cancel()
        if to_reject:
            to_reject._reverse_moves(cancel=True)
        return {'type': 'ir.actions.act_window_close', 'infos': 'validate'}

    def button_continue(self):
        return {'type': 'ir.actions.act_window_close', 'infos': 'validate'}

    def button_cancel(self):
        """ Cancel the current operation and invalidate the current "Validate" action. """
        return True
