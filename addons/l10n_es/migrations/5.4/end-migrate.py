from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
<<<<<<< 4e703b5fa92589d774421a5b9ca58c1647200823
    for company in env['res.company'].search([('chart_template', 'like', r'es\_%')], order="parent_path"):
        env['account.chart.template'].try_loading(company.chart_template, company, force_create=False)
||||||| 00df952724fd5ba444db08a271bebbff76b98808
    for company in env['res.company'].search([('chart_template', 'like', r'es\_%')], order="parent_path"):
        env['account.chart.template'].try_loading(company.chart_template, company)
=======
    ChartTemplate = env['account.chart.template']

    companies = env['res.company'].search([('chart_template', '!=', False)], order="parent_path")
    for company in companies:
        if 'es_common' not in ChartTemplate._get_parent_template(company.chart_template):
            continue
        ChartTemplate.try_loading(company.chart_template, company)
>>>>>>> d422c3fbf85094aab711ebd744b3255f22131b26
