from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([('chart_template', 'like', r'es\_%'), ('parent_id', '=', False)]):
        # See commit d3c7e51e94d98da9086a3817b157c4e125c80790 for details
        ChartTemplate = env["account.chart.template"].with_company(company)

        tax_s_iva0_g_i = ChartTemplate.ref("account_tax_template_s_iva0_g_i", raise_if_not_found=False)
        if tax_s_iva0_g_i and tax_s_iva0_g_i.l10n_es_type == 'no_sujeto_loc' and not tax_s_iva0_g_i.l10n_es_exempt_reason:
            tax_s_iva0_g_i.write({
                'l10n_es_type': 'exento',
                'l10n_es_exempt_reason': 'E5',
            })

        tax_s_iva0_g_e = ChartTemplate.ref("account_tax_template_s_iva0_g_e", raise_if_not_found=False)
        if tax_s_iva0_g_e and tax_s_iva0_g_e.l10n_es_type == 'no_sujeto_loc' and not tax_s_iva0_g_e.l10n_es_exempt_reason:
            tax_s_iva0_g_e.write({
                'l10n_es_type': 'exento',
                'l10n_es_exempt_reason': 'E2',
            })
