# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_setup_certification_done = fields.Boolean('Certification downloaded', default=False, help="True iff the certification website has been accessed via account's setup bar.")

    @api.model
    def setting_certification_action(self):
        current_company = self.env['res.company']._company_default_get()
        current_company.l10n_fr_setup_certification_done = True
        return {
            'type': 'ir.actions.act_url',
            'url': 'http://www.odoo.com', #TODO put the right URL for certification website here
            'target': 'self',
        }