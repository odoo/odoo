# -*- coding: utf-8 -*-
import logging

from odoo.tests import standalone


_logger = logging.getLogger(__name__)


@standalone('all_l10n')
def test_all_l10n(env):
    """ This test will install all the l10n_* modules.
    As the module install is not yet fully transactional, the modules will
    remain installed after the test.
    """
    # Ensure the presence of demo data, to see if they can be correctly installed
    assert env.ref('base.module_account').demo, "Need the demo to test with data"

    mapping = env['account.chart.template'].get_chart_template_mapping()

    # Install the requiriments
    modules_collection = [template['modules'] for template in mapping.values()]
    l10n_mods_names = [module for modules in modules_collection for module in modules]
    l10n_mods = env['ir.module.module'].search([('name', 'in', l10n_mods_names), ('state', '=', 'uninstalled')])
    _logger.info('Modules to be installed: [%s]', ', '.join(l10n_mods_names))
    l10n_mods.button_immediate_install()
    env.reset()
    env = env()

    # Install Charts of Accounts
    companies = env['res.company'].create([{
        'name': f'company_coa_{template_code}',
        'country_id': env.ref(template['country']).id,
    } for template_code, template in mapping.items()])
    companies_dict = {company.name[len('company_coa_'):]: company for company in companies}

    # Install the CoAs
    for template_code, company in companies_dict.items():
        env.user.company_ids += company
        env.user.company_id = company
        _logger.info('Testing COA: %s (company: %s)', template_code, company.name)
        try:
            with env.cr.savepoint():
                env['account.chart.template'].try_loading(template_code, company, install_demo=True)
        except Exception:
            _logger.error("Error when creating COA %s", template_code, exc_info=True)
