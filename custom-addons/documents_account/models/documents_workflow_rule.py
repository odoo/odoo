# -*- coding: utf-8 -*-
from odoo import models, fields, api


class WorkflowActionRuleAccount(models.Model):
    _inherit = ['documents.workflow.rule']

    create_model = fields.Selection(selection_add=[('account.move.in_invoice', "Vendor bill"),
                                                   ('account.move.out_invoice', 'Customer invoice'),
                                                   ('account.move.in_refund', 'Vendor Credit Note'),
                                                   ('account.move.out_refund', "Credit note"),
                                                   ('account.move.entry', "Miscellaneous Operations"),
                                                   ('account.bank.statement', "Bank Statement"),
                                                   ('account.move.in_receipt', "Purchase Receipt")])
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        company_dependent=True,
        domain="[('id', 'in', suitable_journal_ids)]",
    )
    suitable_journal_ids = fields.Many2many('account.journal', compute='_compute_suitable_journal_ids')
    display_journal_id = fields.Boolean(compute='_compute_suitable_journal_ids')
    move_type = fields.Char(compute='_compute_move_type')

    @api.constrains('journal_id', 'create_model')
    def _check_journal_id(self):
        # As journal_id is company_dependant it can't be computed.
        # A constrain is used so that it gets default values on
        # write/create.
        for record in self:
            if record.journal_id not in record.suitable_journal_ids:
                record.journal_id = record.suitable_journal_ids[:1]

    @api.depends('create_model')
    def _compute_move_type(self):
        for rule in self:
            move_type = False
            if rule.create_model and (rule.create_model.startswith(('account.move', 'account.bank.statement'))):
                move_type = rule.create_model.split('.')[2]
            rule.move_type = move_type

    @api.depends('move_type')
    @api.depends_context('company')
    def _compute_suitable_journal_ids(self):
        company_journals = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(self.env.company),
        ])
        for rule in self:
            if company_journals:
                if rule.move_type == 'statement':
                    rule.suitable_journal_ids = company_journals.filtered(lambda journal: journal.type == 'bank')
                else:
                    move = self.env['account.move'].new({'move_type': rule.move_type})
                    rule.suitable_journal_ids = rule.move_type and move.suitable_journal_ids._origin
                rule.display_journal_id = bool(rule.move_type)
            else:
                rule.suitable_journal_ids = False
                rule.display_journal_id = False

    def create_record(self, documents=None):
        rv = super(WorkflowActionRuleAccount, self).create_record(documents=documents)
        if self.create_model.startswith('account.move'):
            move = None
            invoice_ids = []

            # 'entry' are outside of document loop because the actions
            #  returned could be differents (cfr. l10n_be_soda)
            if self.move_type == 'entry':
                return self.journal_id.create_document_from_attachment(attachment_ids=documents.attachment_id.ids)

            for document in documents:
                if document.res_model == 'account.move' and document.res_id:
                    move = self.env['account.move'].browse(document.res_id)
                else:
                    move = self.journal_id\
                        .with_context(default_move_type=self.move_type)\
                        ._create_document_from_attachment(attachment_ids=document.attachment_id.id)
                partner = self.partner_id or document.partner_id
                if partner:
                    move.partner_id = partner
                if move.statement_line_id:
                    move['suspense_statement_line_id'] = move.statement_line_id.id

                invoice_ids.append(move.id)

            context = dict(self._context, default_move_type=self.move_type)
            action = {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'name': "Invoices",
                'view_id': False,
                'view_mode': 'tree',
                'views': [(False, "list"), (False, "form")],
                'domain': [('id', 'in', invoice_ids)],
                'context': context,
            }
            if len(invoice_ids) == 1:
                record = move or self.env['account.move'].browse(invoice_ids[0])
                view_id = record.get_formview_id() if record else False
                action.update({
                    'view_mode': 'form',
                    'views': [(view_id, "form")],
                    'res_id': invoice_ids[0],
                    'view_id': view_id,
                })
            return action

        elif self.create_model == 'account.bank.statement':
            # only the journal type is checked as journal will be retrieved from
            # the bank account later on. Also it is not possible to link the doc
            # to the newly created entry as they can be more than one. But importing
            # many times the same bank statement is later checked.
            default_journal = self.journal_id or self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
            return default_journal.create_document_from_attachment(attachment_ids=documents.attachment_id.ids)

        return rv
