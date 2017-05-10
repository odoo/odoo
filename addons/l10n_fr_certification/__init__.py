# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import models
from odoo import api, SUPERUSER_ID

def _setup_inalterability(cr, registry):
    # make sure account_cancel is not usable at the same time as l10n_fr
    # FORWARD PORT NOTICE
    # In master as of March 2017, RCO-ODOO coded an exclusive field on modules to flag incompatibility

    env = api.Environment(cr, SUPERUSER_ID, {})
    wanted_states = ['installed', 'to upgrade', 'to install']
    account_cancel_module = env['ir.module.module'].search([('name', '=', 'account_cancel')], limit=1)

    if account_cancel_module and account_cancel_module.state in wanted_states:
        views_xml_id = env['ir.model.data'].search([('module', '=', 'account_cancel'), ('model', '=', 'ir.ui.view')])
        ir_views = env['ir.ui.view'].browse([v.res_id for v in views_xml_id])
        ir_views.write({'active': False})

    fr_companies = env['res.company'].search([('country_id', '=', env.ref('fr'))])
    if fr_companies:
        # create the securisation sequence per company
        fr_companies._create_secure_sequence()

        #reset the update_posted field on journals
        journals = env['account.journal'].search([('company_id', 'in', fr_companies.ids)])
        if journals:
            journals.write({'update_posted': False})
