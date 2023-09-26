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

    # Install the requiriments
    l10n_mods = env['ir.module.module'].search([
        ('name', '=like', 'l10n%'),
        ('state', '=', 'uninstalled'),
    ])
    l10n_mods.button_immediate_install()
    env.reset()     # clear the set of environments
    env = env()     # get an environment that refers to the new registry

    # Install Charts of Accounts
    already_loaded_codes = set(env['res.company'].search([]).mapped('chart_template'))
    not_loaded_codes = [
        (template_code, template)
        for template_code, template in env['account.chart.template']._get_chart_template_mapping().items()
        if template_code not in already_loaded_codes
    ]
    companies = env['res.company'].create([
        {
            'name': f'company_coa_{template_code}',
            'country_id': template['country_id'],
        }
        for template_code, template in not_loaded_codes
    ])

    # Install the CoAs
    for (template_code, _template), company in zip(not_loaded_codes, companies):
        env.user.company_ids += company
        env.user.company_id = company
        _logger.info('Testing COA: %s (company: %s)', template_code, company.name)
        try:
            with env.cr.savepoint():
                env['account.chart.template'].try_loading(template_code, company, install_demo=True)
        except Exception:
            _logger.error("Error when creating COA %s", template_code, exc_info=True)
