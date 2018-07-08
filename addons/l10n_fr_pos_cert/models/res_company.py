# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_pos_cert_sequence_id = fields.Many2one('ir.sequence')

    @api.model
    def create(self, vals):
        company = super(ResCompany, self).create(vals)
        #when creating a new french company, create the securisation sequence as well
        if company._is_accounting_unalterable():
            sequence_fields = ['l10n_fr_pos_cert_sequence_id']
            company._create_secure_sequence(sequence_fields)
        return company

    @api.multi
    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        #if country changed to fr, create the securisation sequence
        for company in self:
            if company._is_accounting_unalterable():
                sequence_fields = ['l10n_fr_pos_cert_sequence_id']
                company._create_secure_sequence(sequence_fields)
        return res
