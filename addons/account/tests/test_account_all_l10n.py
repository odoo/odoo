# -*- coding: utf-8 -*-
import logging

from odoo.tests import standalone
from odoo.tests import tagged, SavepointCase


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

    coas = env['account.chart.template'].search([])
    for coa in coas:
        cname = 'company_%s' % str(coa.id)
        company = env['res.company'].create({'name': cname})
        env.user.company_ids += company
        env.user.company_id = company
        _logger.info('Testing COA: %s (company: %s)' % (coa.name, cname))
        try:
            with env.cr.savepoint():
                coa.try_loading()
        except Exception:
            _logger.error("Error when creating COA %s", coa.name, exc_info=True)


@tagged('post_install', '-at_install')
class TestDemoInstalled(SavepointCase):
    def test_demo_installed(self):
        if not self.env.ref('base.module_account').demo:
            self.skipTest("Need demo data to test that it is installed...")
        countries_installed = {
             meta['xmlid'].split('.')[0]
             for meta in self.env['account.chart.template'].search([]).get_metadata()
             if meta['xmlid'] and meta['xmlid'] != 'l10n_generic_coa.configurable_chart_template'
        }
        countries_instantiated = {
            meta['xmlid'].split('.')[0]
            for meta in self.env['res.company'].search([
                ('id', '!=', self.env.ref('base.main_company').id)
            ]).chart_template_id.get_metadata()
        }
        self.assertFalse(countries_installed - countries_instantiated)
