# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from odoo import api, SUPERUSER_ID
from .models.res_company import UNALTERABLE_COUNTRIES


def _setup_inalterability(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # enable ping for this module
    env['publisher_warranty.contract'].update_notification(cron_mode=True)

    de_companies = env['res.company'].search([('partner_id.country_id.code', 'in', UNALTERABLE_COUNTRIES)])
    if de_companies:
        #reset the update_posted field on journals
        journals = env['account.journal'].search([('company_id', 'in', de_companies.ids)])
        journals.write({'update_posted': False})
