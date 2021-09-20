# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # == Business fields ==
    payment_token_id = fields.Many2one(
        comodel_name='payment.token',
        string="Saved payment token",
        store=True, readonly=False,
        compute='_compute_payment_token_id',
        domain='''[
            (payment_method_code == 'electronic', '=', 1),
            ('company_id', '=', company_id),
            ('acquirer_id.capture_manually', '=', False),
            ('acquirer_id.journal_id', '=', journal_id),
            ('partner_id', 'in', suitable_payment_token_partner_ids),
        ]''',
        help="Note that tokens from acquirers set to only authorize transactions (instead of capturing the amount) are "
             "not available.")

    # == Display purpose fields ==
    suitable_payment_token_partner_ids = fields.Many2many(
        comodel_name='res.partner',
        compute='_compute_suitable_payment_token_partner_ids')
    payment_method_code = fields.Char(
        related='payment_method_id.code')

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('can_edit_wizard')
    def _compute_suitable_payment_token_partner_ids(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                lines = wizard._get_batches()[0]['lines']
                partners = lines.partner_id
                commercial_partners = partners.commercial_partner_id
                children_partners = commercial_partners.child_ids
                wizard.suitable_payment_token_partner_ids = (partners + commercial_partners + children_partners)._origin
            else:
                wizard.suitable_payment_token_partner_ids = False

    @api.onchange('can_edit_wizard', 'payment_method_id', 'journal_id')
    def _compute_payment_token_id(self):
        for wizard in self:
            if wizard.can_edit_wizard \
                    and wizard.payment_method_id.code == 'electronic' \
                    and wizard.journal_id \
                    and wizard.suitable_payment_token_partner_ids:
                wizard.payment_token_id = self.env['payment.token'].search([
                    ('partner_id', 'in', wizard.suitable_payment_token_partner_ids.ids),
                    ('acquirer_id.capture_manually', '=', False),
                    ('acquirer_id.journal_id', '=', wizard.journal_id.id),
                 ], limit=1)
            else:
                wizard.payment_token_id = False

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _create_payment_vals_from_wizard(self):
        # OVERRIDE
        payment_vals = super()._create_payment_vals_from_wizard()
        payment_vals['payment_token_id'] = self.payment_token_id.id
        return payment_vals

    def _init_payments(self, to_process, edit_mode=False):
        # OVERRIDE
        # Delay the reconciliation between payment & invoices when an electronic transaction is needed using a token.
        for vals in to_process:
            if vals['create_vals'].get('payment_token_id'):
                invoices = vals['to_reconcile'].move_id.filtered(lambda x: x.is_invoice(include_receipts=True))
                vals['transaction_invoices'] = invoices

        return super()._init_payments(to_process, edit_mode=edit_mode)

    def _post_payments(self, to_process, edit_mode=False):
        # OVERRIDE
        # Create a payment transaction for the newly created payments and link them to the related invoices.
        for vals in to_process:
            payment = vals['payment']
            if payment.payment_token_id:
                payment._create_payment_transaction({'invoice_ids': [(6, 0, vals['transaction_invoices'].ids)]})

        return super()._post_payments(to_process, edit_mode=edit_mode)

    def _reconcile_payments(self, to_process, edit_mode=False):
        # OVERRIDE
        # Don't reconcile payments for which the payment transactions failed.
        to_process = [x for x in to_process if x['payment'].state == 'posted']

        return super()._reconcile_payments(to_process, edit_mode=edit_mode)
