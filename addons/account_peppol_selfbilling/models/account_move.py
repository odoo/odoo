from odoo import _, models, fields


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

    def _get_mail_template(self):
        if all(move.move_type == 'in_invoice' and move.journal_id.is_self_billing for move in self):
            return self.env.ref('account_peppol_selfbilling.email_template_edi_self_billing_invoice')
        elif all(move.move_type == 'in_refund' and move.journal_id.is_self_billing for move in self):
            return self.env.ref('account_peppol_selfbilling.email_template_edi_self_billing_credit_note')
        return super()._get_mail_template()

    def _is_exportable_as_self_invoice(self):
        return (
            self.state == 'posted'
            and self.is_purchase_document()
            and (invoice_edi_format := self.commercial_partner_id._get_peppol_edi_format())
            and (edi_builder := self.partner_id._get_edi_builder(invoice_edi_format)) is not None
            and edi_builder._can_export_selfbilling()
            and self.journal_id.is_self_billing
        )

    def _get_last_sequence_domain(self, relaxed=False):
        # EXTENDS 'account'
        where_string, param = super()._get_last_sequence_domain(relaxed)
        if self.journal_id.type == 'purchase' and self.journal_id.is_self_billing:
            if self.partner_id:
                where_string += " AND commercial_partner_id = %(partner_id)s "
                param['partner_id'] = self.partner_id.commercial_partner_id.id
            else:
                where_string += " AND false "

        return where_string, param

    def _get_starting_sequence(self):
        # EXTENDS 'account'
        self.ensure_one()

        if not (self.journal_id.type == 'purchase' and self.journal_id.is_self_billing):
            return super()._get_starting_sequence()

        partner_identifier = str(self.partner_id.commercial_partner_id.id) if self.partner_id else _('[Partner id]')
        move_date = self.date or self.invoice_date or fields.Date.context_today(self)
        starting_sequence = "%s%s/%04d/%02d/0000" % (
            self.journal_id.code,
            partner_identifier.zfill(5),
            move_date.year,
            move_date.month,
        )
        if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
            starting_sequence = "R" + starting_sequence
        if self.journal_id.payment_sequence and self.payment_id:
            starting_sequence = "P" + starting_sequence
        return starting_sequence
