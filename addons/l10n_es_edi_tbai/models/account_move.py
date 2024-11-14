# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from markupsafe import Markup
from psycopg2.errors import LockNotAvailable

from odoo import _, api, fields, models
from odoo.exceptions import UserError

TBAI_REFUND_REASONS = [
    ('R1', "R1: Art. 80.1, 80.2, 80.6 and rights founded error"),
    ('R2', "R2: Art. 80.3"),
    ('R3', "R3: Art. 80.4"),
    ('R4', "R4: Art. 80 - other"),
    ('R5', "R5: Factura rectificativa en facturas simplificadas"),
]


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_es_tbai_state = fields.Selection([
            ('to_send', 'To Send'),
            ('sent', 'Sent'),
            ('cancelled', 'Cancelled'),
        ],
        string='TicketBAI status',
        compute='_compute_l10n_es_tbai_state',
    )
    l10n_es_tbai_chain_index = fields.Integer(
        string="TicketBAI chain index",
        help="Invoice index in chain, set if and only if an in-chain XML was submitted and did not error",
        related='l10n_es_tbai_post_document_id.chain_index',
    )

    l10n_es_tbai_post_document_id = fields.Many2one(
        comodel_name='l10n_es_edi_tbai.document',
        readonly=True,
        copy=False,
    )
    l10n_es_tbai_cancel_document_id = fields.Many2one(
        comodel_name='l10n_es_edi_tbai.document',
        readonly=True,
        copy=False,
    )

    l10n_es_tbai_post_file = fields.Binary(
        string="TicketBAI Post File",
        related='l10n_es_tbai_post_document_id.xml_attachment_id.datas',
    )
    l10n_es_tbai_post_file_name = fields.Char(
        string="TicketBAI Post Attachment Name",
        related="l10n_es_tbai_post_document_id.xml_attachment_id.name",
    )
    l10n_es_tbai_cancel_file = fields.Binary(
        string="TicketBAI Cancel File",
        related='l10n_es_tbai_cancel_document_id.xml_attachment_id.datas',
    )
    l10n_es_tbai_cancel_file_name = fields.Char(
        string="TicketBAI Cancel File Name",
        related='l10n_es_tbai_cancel_document_id.xml_attachment_id.name',
    )

    l10n_es_tbai_is_required = fields.Boolean(
        string="TicketBAI required",
        help="Is the Basque EDI (TicketBAI) needed ?",
        compute='_compute_l10n_es_tbai_is_required',
    )

    l10n_es_tbai_refund_reason = fields.Selection(
        selection=TBAI_REFUND_REASONS,
        string="Invoice Refund Reason Code (TicketBai)",
        help="BOE-A-1992-28740. Ley 37/1992, de 28 de diciembre, del Impuesto sobre el "
        "Valor Añadido. Artículo 80. Modificación de la base imponible.",
        copy=False,
    )
    l10n_es_tbai_reversed_ids = fields.Many2many(
        'account.move', 'account_move_tbai_reversed_moves', 'refund_id', 'reversed_move_id',
        string="Refunded Vendor Bills",
        domain="[('move_type', '=', 'in_invoice'), ('commercial_partner_id', '=', commercial_partner_id)]",
        help="In the case where a vendor refund has multiple original invoices, you can set them here. ",
    )

    # -------------------------------------------------------------------------
    # API-DECORATED & EXTENDED METHODS
    # -------------------------------------------------------------------------

    @api.depends('l10n_es_tbai_post_document_id.state', 'l10n_es_tbai_cancel_document_id.state')
    def _compute_l10n_es_tbai_state(self):
        for move in self:
            state = 'to_send' if move.l10n_es_tbai_is_required else None
            if move.l10n_es_tbai_post_document_id and move.l10n_es_tbai_post_document_id.state == 'accepted':
                state = 'sent'
            if move.l10n_es_tbai_cancel_document_id and move.l10n_es_tbai_cancel_document_id.state == 'accepted':
                state = 'cancelled'

            move.l10n_es_tbai_state = state

    @api.depends('move_type', 'company_id')
    def _compute_l10n_es_tbai_is_required(self):
        for move in self:
            move.l10n_es_tbai_is_required = (
                move.company_id.l10n_es_tbai_is_enabled
                and (
                    move.is_sale_document()
                    or move.is_purchase_document() and move.company_id.l10n_es_tbai_tax_agency == 'bizkaia'
                )
                and any(not line._l10n_es_tbai_is_ignored() for line in move.invoice_line_ids)
            )

    @api.depends('l10n_es_tbai_post_document_id.chain_index')
    def _compute_show_reset_to_draft_button(self):
        # EXTENDS account_edi account.move
        super()._compute_show_reset_to_draft_button()

        for move in self:
            if move.l10n_es_tbai_chain_index:
                move.show_reset_to_draft_button = False

    def button_draft(self):
        # EXTENDS account account.move
        for move in self:
            if move.l10n_es_tbai_chain_index and move.l10n_es_tbai_state != 'cancelled':
                # NOTE this last condition (state is cancelled) is there because
                # button_cancel calls button_draft.
                # Draft button does not appear for user.
                raise UserError(_("You cannot reset to draft an entry that has been posted to TicketBAI's chain"))
        super().button_draft()

    @api.ondelete(at_uninstall=False)
    def _l10n_es_tbai_unlink_except_in_chain(self):
        # Prevent deleting moves that are part of the TicketBAI chain
        if not self._context.get('force_delete') and any(m.l10n_es_tbai_chain_index for m in self):
            raise UserError(_('You cannot delete a move that has a TicketBAI chain id.'))

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _l10n_es_tbai_check_can_send(self):
        # Ensure the move is posted
        if self.state != 'posted':
            return _("Cannot send an entry that is not posted to TicketBAI.")
        if self.l10n_es_tbai_state in ('sent', 'cancelled'):
            return _("This entry has already been posted.")

    def _l10n_es_tbai_get_attachment_name(self, cancel=False):
        return self.name + ('_post.xml' if not cancel else '_cancel.xml')

    def _l10n_es_tbai_create_edi_document(self, cancel=False):
        return self.env['l10n_es_edi_tbai.document'].sudo().create({
            'name': self.name,
            'date': self.date,
            'company_id': self.company_id.id,
            'is_cancel': cancel,
        })

    def _l10n_es_tbai_post_document_in_chatter(self, message, cancel=False):
        test_suffix = '(test mode)' if self.company_id.l10n_es_tbai_test_env else ''
        self.with_context(no_new_invoice=True).message_post(
            body=Markup("<pre>TicketBAI: posted {document_type} XML {test_suffix}\n{message}</pre>").format(
                document_type='emission' if not cancel else 'cancellation',
                test_suffix=test_suffix,
                message=message,
            ),
            attachment_ids=[self.l10n_es_tbai_post_document_id.xml_attachment_id.id] if not cancel else [self.l10n_es_tbai_cancel_document_id.xml_attachment_id.id],
        )

    def _l10n_es_tbai_lock_move(self):
        """ Acquire a write lock on the invoices in self. """
        self.ensure_one()

        try:
            with self.env.cr.savepoint(flush=False):
                self.env.cr.execute('SELECT * FROM account_move WHERE id = %s FOR UPDATE NOWAIT', [self.id])
        except LockNotAvailable:
            raise UserError(_('Cannot send this entry as it is already being processed.'))

    # -------------------------------------------------------------------------
    # WEB SERVICE CALLS
    # -------------------------------------------------------------------------

    def l10n_es_tbai_send_bill(self):
        for bill in self:
            error = bill._l10n_es_tbai_post()
            if self.env['account.move.send']._can_commit():
                self._cr.commit()
            if error:
                raise UserError(error)

    def l10n_es_tbai_cancel(self):
        for invoice in self:
            invoice._l10n_es_tbai_lock_move()

            if invoice.l10n_es_tbai_cancel_document_id and invoice.l10n_es_tbai_cancel_document_id.state == 'rejected':
                invoice.l10n_es_tbai_cancel_document_id.sudo().unlink()

            if not invoice.l10n_es_tbai_cancel_document_id:
                invoice.l10n_es_tbai_cancel_document_id = invoice._l10n_es_tbai_create_edi_document(cancel=True)

            edi_document = invoice.l10n_es_tbai_cancel_document_id

            error = edi_document._post_to_web_service(invoice._l10n_es_tbai_get_values(cancel=True))
            if error:
                raise UserError(error)

            if edi_document.state == 'accepted':
                invoice.button_cancel()
                invoice._l10n_es_tbai_post_document_in_chatter(edi_document.response_message, cancel=True)

            if self.env['account.move.send']._can_commit():
                self._cr.commit()

            if edi_document.state != 'accepted':
                raise UserError(edi_document.response_message)

    def _l10n_es_tbai_post(self):
        self.ensure_one()

        # Avoid the move to be sent if it is being modified by a parallel transaction (for example reset to draft)
        # It will also avoid the move to be sent by different parallel transactions
        self._l10n_es_tbai_lock_move()

        error = self._l10n_es_tbai_check_can_send()
        if error:
            return error

        if self.l10n_es_tbai_post_document_id and self.l10n_es_tbai_post_document_id.state == 'rejected':
            self.l10n_es_tbai_post_document_id.sudo().unlink()

        if not self.l10n_es_tbai_post_document_id:
            self.l10n_es_tbai_post_document_id = self._l10n_es_tbai_create_edi_document()

        edi_document = self.l10n_es_tbai_post_document_id

        error = edi_document._post_to_web_service(self._l10n_es_tbai_get_values())
        if error:
            return error

        if edi_document.state == 'accepted':
            self._l10n_es_tbai_post_document_in_chatter(edi_document.response_message)
            return

        # Return the error message if the xml document was not accepted
        return edi_document.response_message

    # -------------------------------------------------------------------------
    # XML DOCUMENT
    # -------------------------------------------------------------------------

    def _l10n_es_tbai_get_values(self, cancel=False):
        values = {
            'is_sale': self.is_sale_document(),
            'partner': self.commercial_partner_id,
            'is_simplified': self.l10n_es_is_simplified,
            'delivery_date': self.delivery_date if self.delivery_date and self.delivery_date != self.invoice_date else None,
            **self._l10n_es_tbai_get_attachment_values(cancel),
        }
        if values['is_sale']:
            values.update(self._l10n_es_tbai_get_invoice_values(cancel=cancel))

        elif self.company_id.l10n_es_tbai_tax_agency == 'bizkaia':
            values.update(self._l10n_es_tbai_get_vendor_bill_values_batuz())

        return values

    def _l10n_es_tbai_get_attachment_values(self, cancel=False):
        return {
            'attachment_name': self._l10n_es_tbai_get_attachment_name(cancel=cancel),
            'res_model': 'account.move',
            'res_id': self.id,
        }

    def _l10n_es_tbai_get_invoice_values(self, cancel=False):
        self.ensure_one()
        base_amls = self.line_ids.filtered(lambda x: x.display_type == 'product')
        base_lines = [self._prepare_product_base_line_for_taxes_computation(x) for x in base_amls]
        for base_line in base_lines:
            base_line['name'] = base_line['record'].name
        tax_amls = self.line_ids.filtered(lambda x: x.display_type == 'tax')
        tax_lines = [self._prepare_tax_line_for_taxes_computation(x) for x in tax_amls]
        self.env['l10n_es_edi_tbai.document']._add_base_lines_tax_amounts(base_lines, self.company_id, tax_lines=tax_lines)
        taxes = self.invoice_line_ids.tax_ids.flatten_taxes_hierarchy()
        is_oss = any(tax._l10n_es_get_regime_code() == '17' for tax in taxes)

        return {
            **self._l10n_es_tbai_get_credit_note_values(),
            'origin': self.invoice_origin and self.invoice_origin[:250] or 'manual',
            'taxes': taxes,
            'rate':  abs(self.amount_total / self.amount_total_signed) if self.amount_total else 1,
            'base_lines': base_lines,
            'nosujeto_causa': 'IE' if is_oss else 'RL',
            **({'post_doc': self.l10n_es_tbai_post_document_id} if cancel else {}),
        }

    def _l10n_es_tbai_get_credit_note_values(self):
        return {
            'is_refund': self.move_type == 'out_refund',
            'refund_reason': self.l10n_es_tbai_refund_reason,
            'refunded_doc': self.reversed_entry_id.l10n_es_tbai_post_document_id,
            'refunded_doc_invoice_date': self.reversed_entry_id.invoice_date if self.reversed_entry_id else False,
        }

    def _l10n_es_tbai_get_vendor_bill_values_batuz(self):
        """ For the vendor bills for Bizkaia, the structure is different than the regular Ticketbai XML (LROE)"""
        values = {
            'ref': self.ref,
            'is_refund': self.move_type == 'in_refund',
            'invoice_date': self.invoice_date,
            'tipofactura': 'F5' if self._l10n_es_is_dua() else 'F1',
             **self._l10n_es_tbai_get_vendor_bill_tax_values(),
        }
        # Check if intracom
        mod_303_10 = self.env.ref('l10n_es.mod_303_casilla_10_balance')._get_matching_tags()
        mod_303_11 = self.env.ref('l10n_es.mod_303_casilla_11_balance')._get_matching_tags()
        tax_tags = self.invoice_line_ids.tax_ids.flatten_taxes_hierarchy().repartition_line_ids.tag_ids
        intracom = bool(tax_tags & (mod_303_10 + mod_303_11))
        values['regime_key'] = ['09'] if intracom else ['01']
        # Credit notes (factura rectificativa)
        if values['is_refund']:
            values['refund_reason'] = self.l10n_es_tbai_refund_reason
            values['credit_note_invoices'] = self.reversed_entry_id | self.l10n_es_tbai_reversed_ids

        return values

    def _l10n_es_tbai_get_vendor_bill_tax_values(self):
        self.ensure_one()
        results = defaultdict(lambda: {'base_amount': 0.0, 'tax_amount': 0.0})
        amount_total = 0.0
        for line in self.line_ids.filtered(lambda l: l.display_type in ('product', 'tax')):
            if any(t.l10n_es_type == 'ignore' for t in line.tax_ids) or line.tax_line_id.l10n_es_type == 'ignore':
                continue
            if line.tax_line_id.l10n_es_type != 'retencion':
                amount_total += line.balance
            for tax in line.tax_ids.filtered(lambda t: t.l10n_es_type not in ('recargo', 'retencion')):
                results[tax]['base_amount'] += line.balance

            if ((tax := line.tax_line_id) and tax.l10n_es_type not in ('recargo', 'retencion') and
                line.tax_repartition_line_id.factor_percent != -100.0):
                results[tax]['tax_amount'] += line.balance
        iva_values = []
        for tax in results:
            code = "C"  # Bienes Corrientes
            if tax.l10n_es_bien_inversion:
                code = "I"  # Investment Goods
            if tax.tax_scope == 'service':
                code = 'G'  # Gastos
            iva_values.append({'base': results[tax]['base_amount'],
                               'code': code,
                               'tax': results[tax]['tax_amount'],
                               'rec': tax})
        return {'iva_values': iva_values,
                'amount_total': amount_total}

    def _refunds_origin_required(self):
        if self.l10n_es_tbai_is_required:
            return True
        return super()._refunds_origin_required()
