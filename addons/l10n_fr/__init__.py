# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2008 JAILLET Simon - CrysaLEAD - www.crysalead.fr

import models
from odoo import api, SUPERUSER_ID


def _deactivate_account_cancel_views(cr, registry):
    wanted_states = ['installed', 'to upgrade', 'to install']
    env = api.Environment(cr, SUPERUSER_ID, {})
    account_cancel_module = env['ir.module.module'].search([('name', '=', 'account_cancel')], limit=1)

    if account_cancel_module and account_cancel_module.state in wanted_states:
        views_xml_id = env['ir.model.data'].search([('module', '=', 'account_cancel'), ('model', '=', 'ir.ui.view')])
        ir_views = env['ir.ui.view'].browse([v.res_id for v in views_xml_id])
        ir_views.write({'active': False})

    env['account.journal'].search('company_id', '=', env.ref('base.fr').id).write({'update_posted': False})
