import logging

from . import controllers, models, tools

_logger = logging.getLogger(__name__)


def _l10n_it_edi_post_init(env):
    _l10n_it_edi_create_param(env)
    _l10n_it_edi_withholding_post_init(env)


def _l10n_it_edi_create_param(env):
    env['ir.config_parameter'].set_param('l10n_it_edi.proxy_user_edi_mode', 'prod')


def _l10n_it_edi_withholding_post_init(env):
    """ Existing companies that have the Italian Chart of Accounts set """
    for company in env['res.company'].search([('chart_template', '=', 'it'), ('parent_id', '=', False)]):
        ChartTemplate = env['account.chart.template'].with_company(company)
        ChartTemplate._load_data({
            'account.account': ChartTemplate._get_it_withholding_account_account(),
            'account.tax': {
                xml_id: data
                for xml_id, data in ChartTemplate._get_it_withholding_account_tax().items()
                if not ChartTemplate.ref(xml_id, raise_if_not_found=False)
            },
            'account.tax.group': ChartTemplate._get_it_withholding_account_tax_group(),
        })
