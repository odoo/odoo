# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from odoo import api, SUPERUSER_ID, Command
from odoo.addons.account.models.chart_template import update_taxes_from_templates


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Set the new cashflow statement tags based on the templates
    account_templates = env['account.account.template'].search([('chart_template_id', '=', env.ref('l10n_mn.mn_chart_1').id)])
    for company in env['res.company'].search([('chart_template_id', '=', env.ref('l10n_mn.mn_chart_1').id)]):
        for account in env['account.account'].search([('company_id', '=', company.id)]):
            matching_template = account_templates.filtered(lambda account_template: account.code.startswith(account_template.code))
            if matching_template:
                cashflow_tag = matching_template.tag_ids
                if cashflow_tag:
                    account.write({'tag_ids': [Command.link(tag_id) for tag_id in cashflow_tag.ids]})

    # Update all taxes with the new tax repartition lines on templates.
    update_taxes_from_templates(cr, 'l10n_mn.mn_chart_1')
