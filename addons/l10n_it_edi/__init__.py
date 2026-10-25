import logging

from . import controllers, models, tools

_logger = logging.getLogger(__name__)


def _l10n_it_edi_post_init(env):
    env['ir.config_parameter'].set_param('l10n_it_edi.proxy_user_edi_mode', 'prod')

    # Set Italian EDI fields on taxes (we don't need to rewrite them entirely)
    ChartTemplate = env['account.chart.template']
    edi_fields_taxes = ChartTemplate._parse_csv('it', 'account.tax', module='l10n_it_edi')
    ChartTemplate._deref_account_tags('it', edi_fields_taxes)

    for company in env['res.company'].search([('chart_template', '=', 'it'), ('parent_id', '=', False)]):
        CompanyChartTemplate = ChartTemplate.with_company(company)
        CompanyChartTemplate._load_data({
            'account.tax': {
                xmlid: vals
                for xmlid, vals in edi_fields_taxes.items()
                if CompanyChartTemplate.ref(xmlid, raise_if_not_found=False)
            }
        })


def uninstall_hook(env):
    env["res.partner"]._clear_removed_edi_formats("it_edi_xml")
