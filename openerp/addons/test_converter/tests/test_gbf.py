# -*- coding: utf-8 -*-
from openerp.tests import common

class TestGBF(common.TransactionCase):

    def test_group_by_full(self):

        Subs = self.registry('test_converter.test_model.sub')
        TM = self.registry('test_converter.test_model')

        # remove all existing subs (no need to panic, it will be rollbacked...)
        all_subs = Subs.search(self.cr, self.uid, [])
        if all_subs:
            Subs.unlink(self.cr, self.uid, all_subs)

        subs_ids = [Subs.create(self.cr, self.uid, {'name': 'sub%d' % i}) for i in range(5)]
        tm_ids = [TM.create(self.cr, self.uid, {'many2one': subs_ids[i]}) for i in range(3)]

        domain = [('id', 'in', tuple(tm_ids))]

        rg = TM.read_group(self.cr, self.uid, domain, fields=['many2one'], groupby=['many2one'])

        self.assertEqual(len(rg), len(subs_ids))
        rg_subs = sorted(g['many2one'][0] for g in rg)
        self.assertListEqual(rg_subs, sorted(subs_ids))
