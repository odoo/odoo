# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ResCompany(models.Model):
    _name = 'res.company'
    #_inherit = ['res.company', 'mail.thread']

    l10n_fr_secure_sequence_id = fields.Many2one('ir.sequence', 'Sequence to use to ensure the securisation of data', readonly=True)

    #def write(self, vals):
    #    lock_dates = ['period_lock_date', 'fiscalyear_lock_date']
    #    for ld in lock_dates:
    #        if vals.get(ld):
    #            self.message_post(_('User %s has changed %s from %s to %s' % (self.env.user.name,
    #                                                                          ld,
    #                                                                          self[ld],
    #                                                                          vals[ld])))
    #    vals = self._check_secure_sequence(vals)
    #    return super(ResCompany, self).write(vals)

    #@api.model
    #def create(self, vals):
    #    company = super(ResCompany, self).create(vals)
    #    vals = company._check_secure_sequence()
    #    if vals:
    #        super(ResCompany, company).write(vals)
    #    return company

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
                'prefix': 'FRSCR/',
                'suffix': '/%s' % company.id,
                'company_id': company.id}
            seq = self.env['ir.sequence'].create(vals)
            company.write({'l10n_fr_secure_sequence_id': seq.id})

    #def _check_secure_sequence(self, vals={}):
    #    country_id = vals.get('country_id') or self.country_id.id
    #    if country_id == self.env.ref('base.fr').id:
    #        if not self.sequence_secure_id:
    #            vals['sequence_secure_id'] = self._get_secure_sequence().id
    #    return vals
