from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    it_companies = env['res.company'].search([('account_fiscal_country_id.code', '=', 'IT')])
    if not it_companies:
        return

    group_taxes = env['account.tax'].search([
        ('company_id', 'in', it_companies.ids),
        ('amount_type', '=', 'group'),
        ('name', 'in', ['10% SP', '5% SP', '4% SP'])
    ])
    for tax in group_taxes:
        tax.invoice_label = tax.name

    storno_taxes = env['account.tax'].search([
        ('company_id', 'in', it_companies.ids),
        ('name', 'in', ['22% SP neg.', '10% SP neg.', '5% SP neg.', '4% SP neg.'])
    ])

    ve38_tag = env['account.account.tag'].search([('name', '=', 've38')], limit=1)
    if not ve38_tag:
        return

    for tax in storno_taxes:
        for rep_line in tax.repartition_line_ids:
            if rep_line.repartition_type == 'tax':
                if ve38_tag in rep_line.tag_ids:
                    rep_line.tag_ids = [(3, ve38_tag.id)]

            elif rep_line.repartition_type == 'base':
                if ve38_tag not in rep_line.tag_ids:
                    rep_line.tag_ids = [(4, ve38_tag.id)]
