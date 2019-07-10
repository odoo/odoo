# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

UNALTERABLE_COUNTRIES = ['FR', 'MF', 'MQ', 'NC', 'PF', 'RE', 'GF', 'GP', 'TF']


class ResCompany(models.Model):
    _inherit = 'res.company'

    # To do in master : refactor to set sequences more generic

    l10n_fr_secure_sequence_id = fields.Many2one('ir.sequence', 'Sequence to use to ensure the securisation of data', readonly=True)

    @api.model
    def create(self, vals):
        company = super(ResCompany, self).create(vals)
        #when creating a new french company, create the securisation sequence as well
        if company._is_accounting_unalterable():
            sequence_fields = ['l10n_fr_secure_sequence_id']
            company._create_secure_sequence(sequence_fields)
        return company

    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        #if country changed to fr, create the securisation sequence
        for company in self:
            if company._is_accounting_unalterable():
                sequence_fields = ['l10n_fr_secure_sequence_id']
                company._create_secure_sequence(sequence_fields)
        # fiscalyear_lock_date can't be set to a prior date
        if 'fiscalyear_lock_date' in vals or 'period_lock_date' in vals:
            self._check_lock_dates(vals)
        return res

    def _create_secure_sequence(self, sequence_fields):
        """This function creates a no_gap sequence on each companies in self that will ensure
        a unique number is given to all posted account.move in such a way that we can always
        find the previous move of a journal entry.
        """
        for company in self:
            vals_write = {}
            for seq_field in sequence_fields:
                if not company[seq_field]:
                    vals = {
                        'name': 'French Securisation of ' + seq_field + ' - ' + company.name,
                        'code': 'FRSECUR',
                        'implementation': 'no_gap',
                        'prefix': '',
                        'suffix': '',
                        'padding': 0,
                        'company_id': company.id}
                    seq = self.env['ir.sequence'].create(vals)
                    vals_write[seq_field] = seq.id
            if vals_write:
                company.write(vals_write)

    def _is_vat_french(self):
        return self.vat and self.vat.startswith('FR') and len(self.vat) == 13

    def _is_accounting_unalterable(self):
        if not self.vat and not self.country_id:
            return False
        return self.country_id and self.country_id.code in UNALTERABLE_COUNTRIES or self._is_vat_french()
