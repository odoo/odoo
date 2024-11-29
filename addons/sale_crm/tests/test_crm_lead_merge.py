# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.test_crm_lead_merge import TestLeadMergeCommon
from odoo.tests.common import tagged, users


@tagged('lead_manage')
class TestLeadSaleMerge(TestLeadMergeCommon):

    @users('user_sales_manager')
    def test_merge_method_dependencies(self):
        """ Test if dependences for leads are not lost while merging leads. In
        this test leads are ordered as

        lead_w_contact -----------lead---seq=30
        lead_w_email -------------lead---seq=3
        lead_1 -------------------lead---seq=1
        lead_w_partner_company ---lead---seq=1----------------orders
        lead_w_partner -----------lead---seq=False------------orders
        """
        TestLeadMergeCommon.merge_fields.append('order_ids')

        orders = self.env['sale.order'].sudo().create([
            {'partner_id': self.contact_1.id,
             'opportunity_id': self.lead_w_partner_company.id,
            },
            {'partner_id': self.contact_1.id,
             'opportunity_id': self.lead_w_partner.id,
            }
        ])
        self.assertEqual(self.lead_w_partner_company.order_ids, orders[0])
        self.assertEqual(self.lead_w_partner.order_ids, orders[1])

        leads = self.env['crm.lead'].browse(self.leads.ids)._sort_by_confidence_level(reverse=True)
        with self.assertLeadMerged(self.lead_w_contact, leads,
                                   name=self.lead_w_contact.name,
                                   order_ids=orders
                                   ):
            leads._merge_opportunity(auto_unlink=False, max_length=None)
