# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged
from .gstr_test_json import gstr1_test_json, gstr1_test_2_json
import logging
from datetime import date

_logger = logging.getLogger(__name__)

TEST_DATE = date(2023, 5, 20)

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestReports(TestAccountReportsCommon):

    @classmethod
    def l10n_in_reports_gstr1_inv_init(cls, partner=None, tax=None, invoice_line_vals=None, inv=None, post=True):
        if not inv:
            inv = cls.init_invoice(
                "out_invoice",
                products=cls.product_a,
                invoice_date=TEST_DATE,
                taxes=tax,
                company=cls.company_data['company'],
                partner=partner,
            )
        else:
            inv = inv._reverse_moves()
            inv.write({'invoice_date': TEST_DATE})
        if invoice_line_vals:
            inv.write({'invoice_line_ids': [Command.update(l.id, invoice_line_vals) for l in inv.line_ids]})
        if post:
            inv.action_post()
        return inv

    @classmethod
    def _get_tax_from_xml_id(cls, trailing_xmlid):
        return cls.env.ref('account.%s_%s' % (cls.company_data['company'].id, trailing_xmlid))

    @classmethod
    def setUpClass(cls, chart_template_ref="in"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data["company"].write({
            "vat": "24AAGCC7144L6ZE",
            "state_id": cls.env.ref("base.state_in_gj").id,
            "street": "street1",
            "city": "city1",
            "zip": "123456",
            "country_id": cls.env.ref("base.in").id,
        })
        cls.registered_partner_1 = cls.partner_b
        cls.registered_partner_1.write({
            "vat": "27BBBFF5679L8ZR",
            "state_id": cls.env.ref("base.state_in_mh").id,
            "street": "street1",
            "city": "city1",
            "zip": "123456",
            "country_id": cls.env.ref("base.in").id,
            "l10n_in_gst_treatment": "regular",
        })
        cls.registered_partner_2 = cls.partner_b.copy({
            "vat": "24BBBFF5679L8ZR",
            "state_id": cls.env.ref("base.state_in_gj").id
        })
        cls.consumer_partner = cls.registered_partner_2.copy({"vat": None, "l10n_in_gst_treatment": "consumer"})
        cls.deemed_export_partner = cls.registered_partner_1.copy({"l10n_in_gst_treatment": "deemed_export"})
        cls.composition_partner = cls.registered_partner_1.copy({"l10n_in_gst_treatment": "composition"})
        cls.uin_holders_partner = cls.registered_partner_1.copy({"l10n_in_gst_treatment": "uin_holders"})
        cls.large_unregistered_partner = cls.consumer_partner.copy({"state_id": cls.env.ref('base.state_in_mh').id, "l10n_in_gst_treatment": "unregistered"})
        cls.oversea_partner = cls.partner_a
        cls.oversea_partner.write({
            "state_id": cls.env.ref("base.state_us_5").id,
            "street": "street2",
            "city": "city2",
            "zip": "123456",
            "country_id": cls.env.ref("base.us").id,
            "l10n_in_gst_treatment": "overseas",
        })
        cls.product_a.write({"l10n_in_hsn_code": "01111"})
        cls.igst_18 = cls._get_tax_from_xml_id('igst_sale_18')
        cls.sgst_18 = cls._get_tax_from_xml_id('sgst_sale_18')
        cls.exempt_tax = cls._get_tax_from_xml_id('exempt_sale')
        cls.nil_rated_tax = cls._get_tax_from_xml_id('nil_rated_sale')
        cls.non_gst_supplies = cls._get_tax_from_xml_id('non_gst_supplies_sale')

    def test_gstr1_json(self):
        b2b_invoice = self.l10n_in_reports_gstr1_inv_init(self.registered_partner_1, self.igst_18, invoice_line_vals={'price_unit': 500, 'quantity': 2})
        self.l10n_in_reports_gstr1_inv_init(inv=b2b_invoice, invoice_line_vals={'quantity': 1})  # Creates and posts credit note for the above invoice

        b2b_intrastate_invoice = self.l10n_in_reports_gstr1_inv_init(self.registered_partner_2, self.sgst_18, invoice_line_vals={'price_unit': 500, 'quantity': 2})
        self.l10n_in_reports_gstr1_inv_init(inv=b2b_intrastate_invoice, invoice_line_vals={'quantity': 1})

        b2c_intrastate_invoice = self.l10n_in_reports_gstr1_inv_init(self.consumer_partner, self.sgst_18, invoice_line_vals={'price_unit': 500, 'quantity': 2})
        self.l10n_in_reports_gstr1_inv_init(inv=b2c_intrastate_invoice, invoice_line_vals={'quantity': 1})

        b2cl_invoice = self.l10n_in_reports_gstr1_inv_init(self.large_unregistered_partner, self.igst_18, invoice_line_vals={'price_unit': 250000, 'quantity': 1})
        self.l10n_in_reports_gstr1_inv_init(inv=b2cl_invoice, invoice_line_vals={'quantity': 0.5})

        export_invoice = self.l10n_in_reports_gstr1_inv_init(self.oversea_partner, self.igst_18, invoice_line_vals={'price_unit': 500, 'quantity': 2})
        self.l10n_in_reports_gstr1_inv_init(inv=export_invoice, invoice_line_vals={'quantity': 1})

        b2b_invoice_nilratedtax = self.l10n_in_reports_gstr1_inv_init(self.registered_partner_1, self.nil_rated_tax, invoice_line_vals={'price_unit': 500, 'quantity': 2})
        self.l10n_in_reports_gstr1_inv_init(inv=b2b_invoice_nilratedtax, invoice_line_vals={'quantity': 1})

        b2b_invoice_exemptedtax = self.l10n_in_reports_gstr1_inv_init(self.registered_partner_1, self.exempt_tax, invoice_line_vals={'price_unit': 500, 'quantity': 2})
        self.l10n_in_reports_gstr1_inv_init(inv=b2b_invoice_exemptedtax, invoice_line_vals={'quantity': 1})

        b2b_invoice_nongsttax = self.l10n_in_reports_gstr1_inv_init(self.registered_partner_1, self.non_gst_supplies, invoice_line_vals={'price_unit': 500, 'quantity': 2})
        self.l10n_in_reports_gstr1_inv_init(inv=b2b_invoice_nongsttax, invoice_line_vals={'quantity': 1})

        # if no tax is applied then it will be out of scope and not considered in GSTR1
        self.l10n_in_reports_gstr1_inv_init(self.registered_partner_1, [], invoice_line_vals={'price_unit': 500, 'quantity': 2})

        # for b2b invoice with 2 invoice_line_ids having different taxes
        b2b_invoice_gst_and_nil_rated_tax = self.l10n_in_reports_gstr1_inv_init(self.registered_partner_1, self.nil_rated_tax, invoice_line_vals={'price_unit': 700, 'quantity': 2}, post=False)
        existing_line_vals = b2b_invoice.invoice_line_ids[0].read(['product_id', 'account_id', 'price_unit', 'quantity', 'tax_ids'])[0]
        b2b_invoice_gst_and_nil_rated_tax.write({
            'invoice_line_ids': [
                Command.create({
                    'product_id': existing_line_vals['product_id'][0],
                    'account_id': existing_line_vals['account_id'][0],
                    'price_unit': existing_line_vals['price_unit'],
                    'quantity': existing_line_vals['quantity'],
                    'tax_ids': [(6, 0, existing_line_vals['tax_ids'])],
                })
            ]
        })
        b2b_invoice_gst_and_nil_rated_tax.action_post()

        # b2b invoice with special economic zone
        b2b_sez_invoice_gst_and_nil_rated_tax = b2b_invoice_gst_and_nil_rated_tax.copy(default={'l10n_in_gst_treatment': 'special_economic_zone'})
        b2b_sez_invoice_gst_and_nil_rated_tax.action_post()

        gstr1_report = self.env['l10n_in.gst.return.period'].create({
            'company_id': self.company_data["company"].id,
            'periodicity': 'monthly',
            'year': TEST_DATE.strftime('%Y'),
            'month': TEST_DATE.strftime('%m'),
        })
        gstr1_json = gstr1_report._get_gstr1_json()
        self.assertDictEqual(gstr1_json, gstr1_test_json)

    def test_gstr1_json_for_uin_holders_composition_and_deemed_export(self):
        b2b_invoice_deemed_export = self.l10n_in_reports_gstr1_inv_init(self.deemed_export_partner, self.igst_18, invoice_line_vals={'price_unit': 500, 'quantity': 2})
        self.l10n_in_reports_gstr1_inv_init(inv=b2b_invoice_deemed_export, invoice_line_vals={'quantity': 1})  # Creates and posts credit note for the above invoice

        b2b_invoice_composition = self.l10n_in_reports_gstr1_inv_init(self.composition_partner, self.igst_18, invoice_line_vals={'price_unit': 500, 'quantity': 2})
        self.l10n_in_reports_gstr1_inv_init(inv=b2b_invoice_composition, invoice_line_vals={'quantity': 1})

        b2b_invoice_uin_holders = self.l10n_in_reports_gstr1_inv_init(self.uin_holders_partner, self.igst_18, invoice_line_vals={'price_unit': 500, 'quantity': 2})
        self.l10n_in_reports_gstr1_inv_init(inv=b2b_invoice_uin_holders, invoice_line_vals={'quantity': 1})
        gstr1_report = self.env['l10n_in.gst.return.period'].create({
            'company_id': self.company_data["company"].id,
            'periodicity': 'monthly',
            'year': TEST_DATE.strftime('%Y'),
            'month': TEST_DATE.strftime('%m'),
        })
        gstr1_json = gstr1_report._get_gstr1_json()
        self.assertDictEqual(gstr1_json, gstr1_test_2_json)
