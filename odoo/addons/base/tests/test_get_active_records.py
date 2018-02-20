# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestGetActiveRecords(common.TransactionCase):

    def test_get_active_records(self):
        res_partner = self.env['res.partner']
        ids = [9, 35, 30, 18, 17]
        active_records = res_partner.with_context({'active_ids': ids,'active_model': 'res.partner'}).get_active_records()
        self.assertTrue(active_records.ids == ids, "Get correct records for given ids")
        domain = [('id', '<=', 9)]
        records = res_partner.search(domain)
        active_domain_records = res_partner.with_context({'active_domain': domain, 'active_model': 'res.partner'}).get_active_records()
        self.assertEqual(len(active_domain_records), len(records), "Get correct records for given domain")
        self.assertEqual(len(res_partner.with_context({'active_ids': [],'active_model': 'res.partner'}).get_active_records()), 0, "Get Empty Recordset")
        all_partners = res_partner.search([])
        all_records = res_partner.with_context({'active_domain': [], 'active_model': 'res.partner'}).get_active_records()
        self.assertEqual(len(all_records), len(all_partners), "Get all records from res.partner")
