# -*- coding: utf-8 -*-
import logging
import re

from odoo.tests import standalone


_logger = logging.getLogger(__name__)


@standalone('all_l10n')
def test_all_l10n(env):
    """ This test will install all the l10n_* modules.
    As the module install is not yet fully transactional, the modules will
    remain installed after the test.
    """
    l10n_mods = env['ir.module.module'].search([
        ('name', 'like', 'l10n%'),
        ('state', '=', 'uninstalled'),
    ])
    l10n_mods.button_immediate_install()
    env.reset()     # clear the set of environments
    env = env()     # get an environment that refers to the new registry

    CCODERE = re.compile(r'^l10n_(?P<ccode>[a-z]{2})(_.+)?\..+$')
    coas = env['account.chart.template'].search([])
    for coa in coas:
        company = env['res.company'].search([('chart_template_id', '=', coa.id)], limit=1)
        if not company:
            _logger.info('No company found for chart of account %r', coa.name)
            company = env['res.company'].create({'name': 'company_%s' % str(coa.id)})
            # try to find a country
            _, xml_id = coa.get_xml_id().popitem()
            ccre = CCODERE.search(xml_id)
            if ccre:
                country = env['res.country'].search([('code', '=', ccre['ccode'].upper())])
                company.country_id = country.id

        env.user.company_ids += company
        env.user.company_id = company
        _logger.info('Testing COA: %r (company: %r)', coa.name, company.name)
        try:
            with env.cr.savepoint():
                coa.try_loading()
        except Exception:
            _logger.error("Error when creating COA %s", coa.name, exc_info=True)
