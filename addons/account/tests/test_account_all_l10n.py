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
