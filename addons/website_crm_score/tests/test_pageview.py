# -*- coding: utf-8 -*-
from openerp.addons.website_crm_score.tests.common import TestScoring
from psycopg2 import IntegrityError
from openerp.tools import mute_logger


class test_assign(TestScoring):

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_pageview(self):
        cr, uid = self.cr, self.uid

        right_lead = self.pageview.create_pageview(cr, uid, {'lead_id': self.lead0, 'url': 'url2'}, test=True)
        self.assertTrue(right_lead, 'create_pageview should have succeded')

        pg0 = self.pageview.search_read(cr, uid, [('lead_id', '=', self.lead0), ('url', '=', 'url2')], ['view_date'])
        self.assertNotEqual(pg0, [], 'pageview was not created')

        update_lead = self.pageview.create_pageview(cr, uid, {'lead_id': self.lead0, 'url': 'url2'}, test=True)
        self.assertTrue(update_lead, 'create_pageview should have updated the lead')


        self.assertFalse(
            self.pageview.create_pageview(cr, uid, {'lead_id': -1, 'url': 'url2'}, test=True), 
            'create_pageview should not works with unexisting lead id'
        )
