# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError

from collections import defaultdict


class EdiConfig(models.AbstractModel):
    _name = 'edi.config'

    edi_format_ids = fields.Many2many(comodel_name='edi.format',
                                      string='Electronic invoicing',
                                      help='Send XML/EDI invoices',
                                      domain="[('id', 'in', compatible_edi_ids)]",
                                      compute='_compute_edi_format_ids',
                                      readonly=False, store=True)

    compatible_edi_ids = fields.Many2many(comodel_name='edi.format',
                                          compute='_compute_compatible_edi_ids')


    @api.depends('type', 'company_id', 'company_id.account_fiscal_country_id')
    def _compute_compatible_edi_ids(self):
        edi_formats = self.env['edi.format'].search([])

        for journal in self:
            compatible_edis = edi_formats.filtered(lambda e: e._is_compatible_with_journal(journal))
            journal.compatible_edi_ids = compatible_edis

    @api.depends('type', 'company_id', 'company_id.account_fiscal_country_id')
    def _compute_edi_format_ids(self):
        edi_formats = self.env['edi.format'].search([])
        journal_ids = self.ids

        if journal_ids:
            # TODO: who put this ugly mixin-incompatible SQL?, self.env['edi.document'].read_group()
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
                                                                 e._is_enabled_by_default_on_journal(journal))

            # The existing edi formats that are already in use so we can't remove it.
            protected_edi_format_ids = protected_edi_formats_per_journal.get(journal.id, set())
            protected_edi_formats = journal.edi_format_ids.filtered(lambda e: e.id in protected_edi_format_ids)

            journal.edi_format_ids = enabled_edi_formats + protected_edi_formats
