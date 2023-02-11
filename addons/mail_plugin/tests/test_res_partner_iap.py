# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2

from odoo.addons.mail.tests.common import MailCommon
from odoo.tools import mute_logger


class TestResPartnerIap(MailCommon):

    @mute_logger("odoo.sql_db")
    def test_res_partner_iap_constraint(self):
        partner = self.partner_employee

        self.env["res.partner.iap"].search([("partner_id", "=", partner.id)]).unlink()
        self.env["res.partner.iap"].create({"partner_id": partner.id, "iap_enrich_info": "test info"})

        with self.assertRaises(psycopg2.IntegrityError, msg="Can create only one partner IAP per partner"):
            self.env["res.partner.iap"].create({"partner_id": partner.id, "iap_enrich_info": "test info"})

    def test_res_partner_iap_compute_iap_enrich_info(self):
        partner = self.partner_employee

        self.assertFalse(partner.iap_enrich_info)

        partner_iap = self.env["res.partner.iap"].create({"partner_id": partner.id, "iap_enrich_info": "test info"})
        partner.invalidate_cache()
        self.assertEqual(partner.iap_enrich_info, "test info")

        partner_iap.unlink()
        partner.iap_enrich_info = "test info 2"

        partner_iap = self.env["res.partner.iap"].search([("partner_id", "=", partner.id)])
        self.assertTrue(partner_iap, "Should have create the <res.partner.iap>")
        self.assertEqual(partner_iap.iap_enrich_info, "test info 2")

        partner.iap_enrich_info = "test info 3"
        partner_iap.invalidate_cache()
        new_partner_iap = self.env["res.partner.iap"].search([("partner_id", "=", partner.id)])
        self.assertEqual(new_partner_iap, partner_iap, "Should have write on the existing one")
        self.assertEqual(partner_iap.iap_enrich_info, "test info 3")

    def test_res_partner_iap_creation(self):
        partner = self.env['res.partner'].create({
            'name': 'Test partner',
            'iap_enrich_info': 'enrichment information',
            'iap_search_domain': 'qsd@example.com',
        })

        partner.invalidate_cache()

        self.assertEqual(partner.iap_enrich_info, 'enrichment information')
        self.assertEqual(partner.iap_search_domain, 'qsd@example.com')

        partner_iap = self.env['res.partner.iap'].search([('partner_id', '=', partner.id)])
        self.assertEqual(len(partner_iap), 1, 'Should create only one <res.partner.iap>')
        self.assertEqual(partner_iap.iap_enrich_info, 'enrichment information')
        self.assertEqual(partner_iap.iap_search_domain, 'qsd@example.com')

    def test_res_partner_iap_writing(self):
        partner = self.env['res.partner'].create({
            'name': 'Test partner 2',
        })
        partner.write({
            'iap_enrich_info': 'second information',
            'iap_search_domain': 'xyz@example.com',
        })
        partner_iap = self.env['res.partner.iap'].search([('partner_id', '=', partner.id)])
        self.assertEqual(len(partner_iap), 1, 'Should create only one <res.partner.iap>')
        self.assertEqual(partner_iap.iap_enrich_info, 'second information')
        self.assertEqual(partner_iap.iap_search_domain, 'xyz@example.com')

        partner.iap_search_domain = "only write on domain"
        partner_iap.invalidate_cache()
        self.assertEqual(partner_iap.iap_enrich_info, 'second information')
        self.assertEqual(partner_iap.iap_search_domain, 'only write on domain')
