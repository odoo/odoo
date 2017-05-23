# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def retrieve_account_dashboard(self):
        """ Overridden from account in order to add the certification step to
        the setup bar.
        """
        data = super(AccountJournal, self).retrieve_account_dashboard()

        company = self.env['res.company']._company_default_get()
        data['certification'] = company.l10n_fr_setup_certification_done

        return data