# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_secure_sequence_id = fields.Many2one('ir.sequence', 'Sequence to use to ensure the securisation of data', readonly=True)

    @api.model
    def create(self, vals):
        company = super(ResCompany, self).create(vals)
        #when creating a new french company, create the securisation sequence as well
        if company.country_id == self.env.ref('base.fr'):
            company._create_secure_sequence()
        return company

    @api.multi
    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        #if country changed to fr, create the securisation sequence
        if vals.get('country_id') and vals.get('country_id') == self.env.ref('base.fr').id:
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
