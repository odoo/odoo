# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import tools
from . import wizard
from . import controllers
from . import populate

def _mail_post_init_init_alias_domain(env):
    """ Move from ir.config.parameters to real alias domains """
    companies_wo_domain = env['res.company'].search([('alias_domain_id', '=', False)])
    if companies_wo_domain:
        alias_domain = env['mail.alias.domain'].search([])
        if alias_domain:
            return
        catchall_domain = env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")
        if catchall_domain:
            env['mail.alias.domain'].create({
                'company_ids': [(4, company.id) for company in companies_wo_domain],
                'name': catchall_domain,
            })

def _mail_post_init(env):
    _mail_post_init_init_alias_domain(env)
