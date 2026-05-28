from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    can_send_as_self_invoice = fields.Boolean(
        compute='_compute_can_send_as_self_invoice',
    )

    def _compute_can_send_as_self_invoice(self):
        for move in self:
            if move._is_exportable_as_self_invoice():
                move.can_send_as_self_invoice = True
            else:
                move.can_send_as_self_invoice = False

    @api.depends('posted_before', 'state', 'journal_id', 'date', 'move_type', 'payment_id', 'partner_id')
    def _compute_name(self):
        # EXTENDS 'account'
        super()._compute_name()

    @api.onchange('partner_id')
    def _inverse_partner_id(self):
        # EXTENDS 'account'
        super()._inverse_partner_id()
        for invoice in self:
            if invoice.journal_id.is_self_billing and invoice.state == 'draft':
                invoice._set_next_sequence()

    def _get_mail_template(self):
        if all(move.move_type == 'in_invoice' and move.journal_id.is_self_billing for move in self):
            return 'account_peppol_selfbilling.email_template_edi_self_billing_invoice'
        elif all(move.move_type == 'in_refund' and move.journal_id.is_self_billing for move in self):
            return 'account_peppol_selfbilling.email_template_edi_self_billing_credit_note'
        return super()._get_mail_template()

    def _is_exportable_as_self_invoice(self):
        return (
            self.state == 'posted'
            and self.is_purchase_document()
            and self.commercial_partner_id.ubl_cii_format
            and (edi_builder := self.commercial_partner_id._get_edi_builder()) is not None
            and edi_builder._can_export_selfbilling()
            and self.journal_id.is_self_billing
        )

    def _get_last_sequence_domain(self, relaxed=False):
        # EXTENDS 'account'
        where_string, param = super()._get_last_sequence_domain(relaxed)
        if self.journal_id.is_self_billing:
            if self.partner_id:
                where_string += " AND commercial_partner_id = %(partner_id)s "
                param['partner_id'] = self.partner_id.commercial_partner_id.id
            else:
                where_string += " AND false "

        return where_string, param

    def _get_starting_sequence(self):
        # EXTENDS 'account'
        self.ensure_one()

        if not self.journal_id.is_self_billing:
            return super()._get_starting_sequence()

        partner_identifier = str(self.partner_id.commercial_partner_id.id) if self.partner_id else _('[Partner id]')
        starting_sequence = "%s%s/%04d/%02d/0000" % (
            self.journal_id.code,
            partner_identifier.zfill(5),
            self.date.year,
            self.date.month,
        )
        if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
            starting_sequence = "R" + starting_sequence
        if self.journal_id.payment_sequence and self.payment_id:
            starting_sequence = "P" + starting_sequence
        return starting_sequence
