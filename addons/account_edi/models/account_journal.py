# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError

from collections import defaultdict


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    edi_format_ids = fields.Many2many(comodel_name='account.edi.format',
                                      string='Electronic invoicing',
                                      help='Send XML/EDI invoices',
                                      domain="[('id', 'in', compatible_edi_ids)]",
                                      compute='_compute_edi_format_ids',
                                      readonly=False, store=True)

    compatible_edi_ids = fields.Many2many(comodel_name='account.edi.format',
                                          compute='_compute_compatible_edi_ids',
                                          help='EDI format that support moves in this journal')

    def write(self, vals):
        # OVERRIDE
        # Don't allow the user to deactivate an edi format having at least one document to be processed.
        if vals.get('edi_format_ids'):
            old_edi_format_ids = self.edi_format_ids
            res = super().write(vals)
            diff_edi_format_ids = old_edi_format_ids - self.edi_format_ids
            documents = self.env['account.edi.document'].search([
                ('move_id.journal_id', 'in', self.ids),
                ('edi_format_id', 'in', diff_edi_format_ids.ids),
                ('state', 'in', ('to_cancel', 'to_send')),
            ])
            # If the formats we are unchecking do not need a webservice, we don't need them to be correctly sent
            if documents.filtered(lambda d: d.edi_format_id._needs_web_services()):
                raise UserError(_('Cannot deactivate (%s) on this journal because not all documents are synchronized', ', '.join(documents.edi_format_id.mapped('display_name'))))
            # remove these documents which: do not need a web service & are linked to the edi formats we are unchecking
            if documents:
                documents.unlink()
            return res
        else:
            return super().write(vals)

    @api.depends('type', 'company_id', 'company_id.account_fiscal_country_id')
    def _compute_compatible_edi_ids(self):
        edi_formats = self.env['account.edi.format'].search([])

        for journal in self:
            compatible_edis = edi_formats.filtered(lambda e: e._is_compatible_with_journal(journal))
            journal.compatible_edi_ids = compatible_edis

    @api.depends('type', 'company_id', 'company_id.account_fiscal_country_id')
    def _compute_edi_format_ids(self):
        edi_formats = self.env['account.edi.format'].search([])
        journal_ids = self.ids

        if journal_ids:
            self._cr.execute('''
                SELECT
                    move.journal_id,
                    ARRAY_AGG(doc.edi_format_id) AS edi_format_ids
                FROM account_edi_document doc
                JOIN account_move move ON move.id = doc.move_id
                WHERE doc.state IN ('to_cancel', 'to_send')
                AND move.journal_id IN %s
                GROUP BY move.journal_id
            ''', [tuple(journal_ids)])
            protected_edi_formats_per_journal = {r[0]: set(r[1]) for r in self._cr.fetchall()}
        else:
            protected_edi_formats_per_journal = defaultdict(set)

        for journal in self:
            enabled_edi_formats = edi_formats.filtered(lambda e: e._is_compatible_with_journal(journal) and
                                                                 (e._is_enabled_by_default_on_journal(journal)
                                                                  or (e in journal.edi_format_ids)))

            # The existing edi formats that are already in use so we can't remove it.
            protected_edi_format_ids = protected_edi_formats_per_journal.get(journal.id, set())
            protected_edi_formats = journal.edi_format_ids.filtered(lambda e: e.id in protected_edi_format_ids)

            journal.edi_format_ids = enabled_edi_formats + protected_edi_formats

    def _create_document_from_attachment(self, attachment_ids=None):
        # tries to match purchasing orders
        moves = super()._create_document_from_attachment(attachment_ids)
        for move in moves:
            if move.move_type == 'in_invoice':
                references = [move.invoice_origin] if move.invoice_origin else []
                move._find_and_set_purchase_orders(references, move.partner_id.id, move.amount_total, timeout=4)
        return moves
