# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_pos_cert_sequence_id = fields.Many2one(
        'ir.sequence',
        compute='_compute_l10n_fr_pos_cert_sequence_id', store=True,
        copy=False,
    )

    @api.depends('country_id')
    def _compute_l10n_fr_pos_cert_sequence_id(self):
        for company in self:
            if company._is_accounting_unalterable():
                self.env['blockchain.mixin']._create_blockchain_secure_sequence(company, "l10n_fr_pos_cert_sequence_id", company.id)

    def _action_check_l10n_fr_pos_cert_blockchain_integrity(self):
        return self.env.ref('l10n_fr_pos_cert.action_report_l10n_fr_pos_blockchain_integrity').report_action(self.id)
