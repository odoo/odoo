# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from odoo import api, SUPERUSER_ID, Command
from odoo.addons.account.models.chart_template import update_taxes_from_templates


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Set the new cashflow statement tags based on the templates
    account_templates = env['account.account.template'].search([('chart_template_id', '=', env.ref('l10n_mn.mn_chart_1').id)])
    all_account_tags_xmlids = env['account.account.tag'].search([('applicability', '=', 'accounts')]).get_external_id()
    mn_cashflow_tags = env['account.account.tag'].browse([id for id, xmlid in all_account_tags_xmlids.items() if xmlid.startswith('l10n_mn.account_cashflow_tag_')])
    for company in env['res.company'].search([('chart_template_id', '=', env.ref('l10n_mn.mn_chart_1').id)]):
        for account in env['account.account'].search([('company_id', '=', company.id)]):
            matching_template = account_templates.filtered(lambda account_template: account.code.startswith(account_template.code))
            if matching_template:
                cashflow_tags = matching_template.tag_ids & mn_cashflow_tags
                if cashflow_tags:
                    account.write({'tag_ids': [Command.link(tag_id) for tag_id in cashflow_tags.ids]})

    # Update all taxes with the new tax repartition lines on templates.
    update_taxes_from_templates(cr, 'l10n_mn.mn_chart_1')
