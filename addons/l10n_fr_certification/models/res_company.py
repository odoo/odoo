# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models, api
from openerp.exceptions import UserError
from openerp.tools.translate import _

UNALTERABLE_COUNTRIES = ['FR', 'MF', 'MQ', 'NC', 'PF', 'RE', 'GF', 'GP', 'TF']


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_secure_sequence_id = fields.Many2one('ir.sequence', 'Sequence to use to ensure the securisation of data', readonly=True)

    @api.model
    def create(self, vals):
        company = super(ResCompany, self).create(vals)
        #when creating a new french company, create the securisation sequence as well
        if self._is_accounting_unalterable():
            company._create_secure_sequence()
        return company

    @api.multi
    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        #if country changed to fr, create the securisation sequence
        if self._is_accounting_unalterable():
            self.filtered(lambda c: not c.l10n_fr_secure_sequence_id)._create_secure_sequence()
        return res

    def _create_secure_sequence(self):
        """This function creates a no_gap sequence on each companies in self that will ensure
        a unique number is given to all posted account.move in such a way that we can always
        find the previous move of a journal entry.
        """
        for company in self:
            vals = {
                'name': 'French Securisation of account_move_line - ' + company.name,
                'code': 'FRSECUR',
                'implementation': 'no_gap',
                'prefix': '',
                'suffix': '',
                'padding': 0,
                'company_id': company.id}
            seq = self.env['ir.sequence'].create(vals)
            company.write({'l10n_fr_secure_sequence_id': seq.id})

    def _is_vat_french(self):
        return self.vat and self.vat.startswith('FR') and len(self.vat) == 13

    def _is_accounting_unalterable(self, raise_on_nocountry=False):
        if raise_on_nocountry and not self.vat and not self.country_id:
            raise UserError(_('Please set up a country or a VAT number on the company %s.') % self.name, )
        return self.country_id and self.country_id.code in UNALTERABLE_COUNTRIES or self._is_vat_french()
