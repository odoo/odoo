# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.addons.crm.tests.test_crm_lead_merge import TestLeadMergeCommon
from odoo.tests.common import tagged, users
from odoo.tools import mute_logger


@tagged('lead_manage')
class TestLeadMerge(TestLeadMergeCommon):

    @users('user_sales_manager')
    @mute_logger('odoo.models.unlink')
    def test_merge_method_iap_enrich_done(self):
        """Test that the "iap_enrich_done" is set to True if at least one lead have this value True"""
        self.leads.iap_enrich_done = False
        self.lead_w_contact.write({
            'reveal_id': 'test_reveal_id',
            'iap_enrich_done': True,
        })

        leads = self.env['crm.lead'].browse(self.leads.ids)._sort_by_confidence_level(reverse=True)

        with self.assertLeadMerged(leads[0], leads, iap_enrich_done=True, reveal_id='test_reveal_id'):
            leads._merge_opportunity(auto_unlink=False, max_length=None)
