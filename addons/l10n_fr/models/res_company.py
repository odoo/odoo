# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_closing_sequence_id = fields.Many2one(
        'ir.sequence', 'Sequence to use to build sale closings',
        compute='_compute_l10n_fr_closing_sequence_id', store=True,
        copy=False,
    )
    siret = fields.Char(related='partner_id.siret', string='SIRET', size=14, readonly=False)
    ape = fields.Char(string='APE')

    @api.model
    def _get_unalterable_country(self):
        return ['FR', 'MF', 'MQ', 'NC', 'PF', 'RE', 'GF', 'GP', 'TF'] # These codes correspond to France and DOM-TOM.

    def _is_accounting_unalterable(self):
        if not self.vat and not self.country_id:
            return False
        return self.country_id and self.country_id.code in self._get_unalterable_country()

    @api.depends('country_id')
    def _compute_l10n_fr_closing_sequence_id(self):
        for company in self:
            if company._is_accounting_unalterable():
                self.env['blockchain.mixin']._create_blockchain_secure_sequence(company, "l10n_fr_closing_sequence_id", company.id)
