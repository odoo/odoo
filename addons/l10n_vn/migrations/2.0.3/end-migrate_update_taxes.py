from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([('chart_template', '=', 'vn')], order="parent_path"):
<<<<<<< 94d63fb53132b14fb988789e616490894ed2456b
        env['account.chart.template'].try_loading('vn', company, force_create=False)
||||||| 483264fc6cb76d96835ea8cebf50e0a405b88a4f
        env['account.chart.template'].try_loading('vn', company)
=======
        ChartTemplate = env['account.chart.template'].with_company(company)
        data = {
            'account.tax.group': ChartTemplate._get_account_tax_group(company.chart_template),
            'account.tax': ChartTemplate._get_account_tax(company.chart_template)
        }
        ChartTemplate._pre_reload_data(company, {}, data)
        ChartTemplate._load_data(data)
>>>>>>> bdf96f99922a1b7259276efb2032828debfad811
