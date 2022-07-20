# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):

    _inherit = "res.company"

    def _localization_use_documents(self):
        """ This method is to be inherited by localizations and return True if localization use documents """
        self.ensure_one()
        return False

    def write(self, vals):
        companies = False
        if 'country_id' in vals:
            companies = self.filtered(lambda company: company.country_id.id != vals['country_id'])
        result = super(ResCompany, self).write(vals)
        if companies:
            journal_ids = self.env['account.journal'].search([('company_id', 'in', companies.ids)])
            for journal in journal_ids:
                journal._onchange_company()
        return result
