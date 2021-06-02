# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common

class TestGBF(common.TransactionCase):
    def test_group_by_full(self):
        Sub = self.env['test_converter.test_model.sub']
        TM = self.env['test_converter.test_model']

        # remove all existing subs (no need to panic, it will be rollbacked...)
        Sub.search([]).unlink()

        subs_ids = [Sub.create({'name': 'sub%d' % i}).id for i in range(5)]
        tm_ids = [TM.create({'many2one': subs_ids[i]}).id for i in range(3)]

        domain = [('id', 'in', tuple(tm_ids))]
        rg = TM.read_group(domain, fields=['many2one'], groupby=['many2one'])

        self.assertEqual(len(rg), len(subs_ids))
        rg_subs = sorted(g['many2one'][0] for g in rg)
        self.assertListEqual(rg_subs, sorted(subs_ids))
