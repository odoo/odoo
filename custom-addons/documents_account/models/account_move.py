# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    suspense_statement_line_id = fields.Many2one(
        comodel_name='account.bank.statement.line',
        string="Request document from a bank statement line",
        index='btree_not_null',
    )

    def write(self, vals):
        main_attachment_id = vals.get('message_main_attachment_id')
        new_documents = [False for move in self]
        journals_changed = [('journal_id' in vals  and move.journal_id.id != vals['journal_id']) for move in self]
        partner_changed = [(vals.get('partner_id', move.partner_id.id) != move.partner_id.id) for move in self]
        for i, move in enumerate(self):
            if main_attachment_id and not move.env.context.get('no_document') and move.move_type != 'entry':
                previous_attachment_id = move.message_main_attachment_id.id
                document = False
                if previous_attachment_id:
                    document = move.env['documents.document'].sudo().search([('attachment_id', '=', previous_attachment_id)], limit=1)
                if document:
                    document.attachment_id = main_attachment_id
                else:
                    new_documents[i] = True
        res = super().write(vals)
        for new_document, journal_changed, move in zip(new_documents, journals_changed, self):
            if (new_document or journal_changed) and move.message_main_attachment_id:
                move._update_or_create_document(move.message_main_attachment_id.id)
        for partner_changed, move in zip(partner_changed, self):
            if partner_changed:
                move._sync_partner_on_document()
        return res

    def button_reconcile_with_st_line(self):
        """ When using the "Reconciliation Request" next activity on the statement line's chatter, the invoice is linked
        to this statement line through the 'suspense_statement_line_id' field.
        When checking this link on your invoice, you are able to click on a button triggering this method opening the
        bank reconciliation widget for this specific statement line to easily match it with the current invoice.

        :return: An action opening the bank reconciliation widget.
        """
        self.ensure_one()
        st_line = self.suspense_statement_line_id
        rec_pay_lines = self.line_ids.filtered(lambda x: x.account_id.account_type in ('asset_receivable', 'liability_payable'))
        default_todo_command = ','.join(['add_new_amls'] + [str(x) for x in rec_pay_lines.ids])
        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            default_context={
                'search_default_journal_id': st_line.journal_id.id,
                'search_default_statement_id': st_line.statement_id.id,
                'default_journal_id': st_line.journal_id.id,
                'default_st_line_id': st_line.id,
                'default_todo_command': default_todo_command,
            },
        )

    def _update_or_create_document(self, attachment_id):
        if self.company_id.documents_account_settings:
            setting = self.env['documents.account.folder.setting'].sudo().search(
                [('journal_id', '=', self.journal_id.id),
                 ('company_id', '=', self.company_id.id)], limit=1)
            if setting:
                values = {
                    'folder_id': setting.folder_id.id,
                    'partner_id': self.partner_id.id,
                    'owner_id': self.create_uid.id,
                    'tag_ids': [(4, tag.id) for tag in setting.tag_ids],
                }
                Documents = self.env['documents.document'].with_context(default_type='empty').sudo()
                doc = Documents.search([('attachment_id', '=', attachment_id)], limit=1)
                if doc:
                    doc.write(values)
                else:
                    # backward compatibility with documents that may be not
                    # registered as attachments yet
                    values.update({'attachment_id': attachment_id})
                    doc.create(values)

    def _sync_partner_on_document(self):
        for move in self:
            if not move.message_main_attachment_id:
                continue
            doc = self.env['documents.document'].sudo().search([('attachment_id', '=', move.message_main_attachment_id.id)], limit=1)
            if not doc or doc.partner_id == move.partner_id:
                continue
            doc.partner_id = move.partner_id
