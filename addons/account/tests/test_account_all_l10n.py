# -*- coding: utf-8 -*-
import logging

import odoo
from odoo import api
from odoo.tests.common import SingleTransactionCase
from odoo.tests import tagged


_logger = logging.getLogger(__name__)


@tagged('-standard', '-at_install', 'post_install', 'l10nall')
class TestAllL10n(SingleTransactionCase):
    """ This test will install all the l10n_* modules.
    As the module install is not yet fully transactional, the modules will
    remain installed after the test.
    """

    @classmethod
    def setUpClass(cls):
        super(TestAllL10n, cls).setUpClass()
        l10n_mods = cls.env['ir.module.module'].search([
            ('name', 'like', 'l10n%'),
            ('state', '=', 'uninstalled'),
        ])
        _logger.info("Modules to install: %s" % [x.name for x in l10n_mods])
        l10n_mods.button_immediate_install()
        # Now that new modules are installed, we have to reset the environment
        api.Environment.reset()
        cls.env = api.Environment(cls.cr, odoo.SUPERUSER_ID, {})

    def test_all_l10n(self):
        coas = self.env['account.chart.template'].search([])
        for coa in coas:
            cname = 'company_%s' % str(coa.id)
            comp = self.env['res.company'].create({
                'name': cname,
            })
            self.env.user.company_ids += comp
            self.env.user.company_id = comp
            msg = 'Testing COA: %s (company: %s)' % (coa.name, cname)
            _logger.info(msg)
            with self.subTest(msg=msg):
                with self.cr.savepoint():
                    coa.try_loading()
