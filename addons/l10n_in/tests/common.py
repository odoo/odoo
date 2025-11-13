from datetime import date

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo import Command


class L10nInTestInvoicingCommon(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('in')
    def setUpClass(cls):
        super().setUpClass()

        cls.maxDiff = None
        cls.test_date = date(2023, 5, 20)

        # === Countries === #
        cls.country_in = cls.env.ref('base.in')
        cls.country_us = cls.env.ref('base.us')

        # === States === #
        cls.state_in_gj = cls.env.ref('base.state_in_gj')
        cls.state_in_mh = cls.env.ref('base.state_in_mh')
        cls.state_in_hp = cls.env.ref('base.state_in_hp')

        # === Companies === #
        cls.default_company = cls.company_data['company']
        cls.default_company.write({
            'name': "Default Company",
            'state_id': cls.state_in_gj.id,
            'vat': "24AAGCC7144L6ZE",
            'street': "Khodiyar Chowk",
            'street2': "Sala Number 3",
            'city': "Amreli",
            'zip': "365220",
            'l10n_in_is_gst_registered': True,
            'l10n_in_tds_feature': True,
            'l10n_in_tcs_feature': True,
        })

        cls.outside_in_company = cls.env['res.company'].create({
            'name': 'Outside India Company',
            'country_id': cls.country_us.id,
        })

        cls.user.write({
            'company_ids': [cls.default_company.id, cls.outside_in_company.id],
            'company_id': cls.default_company.id,
        })

        # === Partners === #
        cls.partner_a.write({
            'name': "Partner Intra State",
            'vat': '24ABCPM8965E1ZE',
            'state_id': cls.default_company.state_id.id,
            'country_id': cls.country_in.id,
            'street': "Karansinhji Rd",
            'street2': "Karanpara",
            'city': "Rajkot",
            'zip': "360001",
        })

        cls.partner_b.write({
            'vat': '27DJMPM8965E1ZE',
            'state_id': cls.state_in_mh.id,
            'country_id': cls.country_in.id,
            'street': "Sangeet Samrat Naushad Ali Rd",
            'city': "Mumbai",
            'zip': "400052",
        })

        cls.partner_foreign = cls.env['res.partner'].create({
            'name': "Foreign Partner",
            'country_id': cls.country_us.id,
            'state_id': cls.env.ref("base.state_us_1").id,
            'street': "351 Horner Chapel Rd",
            'city': "Peebles",
            'zip': "45660",
        })

        cls.partner_foreign_no_state = cls.env['res.partner'].create({
            'name': "Foreign Partner Without State",
            'country_id': cls.country_us.id,
            # No state_id defined
        })
        cls.sez_partner = cls.env['res.partner'].create({
            'name': 'SEZ Partner',
            'vat': '36AAAAA1234AAZA',
            'l10n_in_gst_treatment': 'special_economic_zone',
            'street': 'Block no. 402',
            'city': 'Some city',
            'zip': '500002',
            'state_id': cls.env.ref('base.state_in_gj').id,
            'country_id': cls.env.ref('base.in').id,
        })

        # === Taxes === #
        AccountChartTemplate = cls.env['account.chart.template']
        cls.sgst_sale_5 = AccountChartTemplate.ref('sgst_sale_5')
        cls.sgst_purchase_5 = AccountChartTemplate.ref('sgst_purchase_5')
        cls.igst_sale_5 = AccountChartTemplate.ref('igst_sale_5')
        cls.igst_sale_18 = AccountChartTemplate.ref('igst_sale_18')
        cls.sgst_sale_18 = AccountChartTemplate.ref('sgst_sale_18')
        cls.igst_sale_18_rcm = AccountChartTemplate.ref('igst_sale_18_rc')
        cls.igst_sale_18_sez_lut = AccountChartTemplate.ref('igst_sale_18_sez_lut')
        cls.igst_sale_18_sez_exp_lut = AccountChartTemplate.ref('igst_sale_18_sez_exp_lut')
        cls.igst_sale_18_sez_exp = AccountChartTemplate.ref('igst_sale_18_sez_exp')
        cls.igst_sale_18_sez_exp_inc = cls.igst_sale_18_sez_exp.copy({'price_include_override': 'tax_included'})
        cls.gst_with_cess = (
            AccountChartTemplate.ref("sgst_sale_12")
            + AccountChartTemplate.ref("cess_5_plus_1591_sale")
        )

        # === Products === #
        cls.product_a.write({
            "l10n_in_hsn_code": "111111",
            'taxes_id': cls.sgst_sale_5,
            'supplier_taxes_id': cls.sgst_purchase_5,
        })

        cls.product_b.write({
            "l10n_in_hsn_code": "111111",
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 1000.0,
            'standard_price': 1000.0,
            'taxes_id': cls.sgst_sale_5.ids,
            'supplier_taxes_id': cls.sgst_purchase_5.ids,
        })
        cls.product_with_cess = cls.env["product.product"].create({
            "name": "product_with_cess",
            "uom_id": cls.env.ref("uom.product_uom_unit").id,
            "lst_price": 1000.0,
            "standard_price": 800.0,
            "property_account_income_id": cls.company_data["default_account_revenue"].id,
            "property_account_expense_id": cls.company_data["default_account_expense"].id,
            "taxes_id": [Command.set(cls.gst_with_cess.ids)],
            "supplier_taxes_id": [Command.set(cls.sgst_purchase_5.ids)],
            "l10n_in_hsn_code": "333333",
        })

        # === Fiscal Positions === #
        cls.fp_in_intra_state = cls.env["account.chart.template"].ref('fiscal_position_in_intra_state')
        cls.fp_in_inter_state = cls.env["account.chart.template"].ref('fiscal_position_in_inter_state')
        cls.fp_in_export = cls.env["account.chart.template"].ref('fiscal_position_in_export_sez_in')

        # === Invoices === #
        cls.invoice_a = cls.init_invoice(
            move_type='out_invoice',
            partner=cls.partner_a,
            amounts=[110, 500],
            taxes=cls.igst_sale_18,
        )

        cls.invoice_b = cls.init_invoice(
            move_type='out_invoice',
            partner=cls.partner_b,
            amounts=[250, 600],
            taxes=cls.igst_sale_18,
        )

        cls.invoice_c = cls.init_invoice(
            move_type='out_invoice',
            partner=cls.partner_foreign,
            amounts=[300, 740],
            taxes=cls.igst_sale_18,
        )

        cls.invoice_d = cls.init_invoice(
            move_type='out_invoice',
            partner=cls.partner_foreign_no_state,
            amounts=[100, 200],
            taxes=cls.igst_sale_18,
        )

        cls.invoice_with_rcm = cls.init_invoice(
            "out_invoice",
            partner=cls.partner_b,
            products=cls.product_a,
            taxes=cls.igst_sale_18_rcm,
        )

        cls.invoice_with_sez_lut = cls.init_invoice(
            "out_invoice",
            partner=cls.sez_partner,
            products=cls.product_a,
            taxes=cls.igst_sale_18_sez_lut,
        )

        cls.invoice_with_sez_without_lut = cls.init_invoice(
            "out_invoice",
            partner=cls.sez_partner,
            products=cls.product_a,
            taxes=cls.igst_sale_18,
        )

        cls.invoice_with_export_lut = cls.init_invoice(
            "out_invoice",
            partner=cls.partner_foreign,
            products=cls.product_a,
            taxes=cls.igst_sale_18_sez_exp_lut,
        )

        cls.invoice_with_export_without_lut = cls.init_invoice(
            "out_invoice",
            partner=cls.partner_foreign,
            products=cls.product_a,
            taxes=cls.igst_sale_18_sez_exp,
        )
        cls.invoice_with_export_without_lut_inc = cls.init_invoice(
            "out_invoice",
            partner=cls.partner_foreign,
            products=cls.product_a,
            taxes=cls.igst_sale_18_sez_exp_inc,
        )

    @classmethod
    def _set_vals_and_post(cls, move, ref=None, line_vals=None, post=True, irn=None):
        if ref:
            move.ref = ref
        if irn:
            move.l10n_in_irn_number = irn

        if line_vals:
            move.write({'invoice_line_ids': [Command.update(line.id, line_vals) for line in move.line_ids]})

        if post:
            move.action_post()
        return move

    @classmethod
    def _init_inv(cls, move_type='out_invoice', company=None, ref=None, partner=None, taxes=None, invoice_date=None, products=None, line_vals=None, post=True, irn=None):
        return cls._set_vals_and_post(
            move=cls.init_invoice(
                move_type,
                products=products or cls.product_a,
                invoice_date=invoice_date or cls.test_date,
                taxes=taxes,
                company=company or cls.default_company,
                partner=partner,
            ),
            ref=ref,
            irn=irn,
            line_vals=line_vals,
            post=post
        )

    @classmethod
    def _create_credit_note(cls, inv, ref=None, credit_note_date=None, line_vals=None, post=True):
        move = inv._reverse_moves()
        move.invoice_date = credit_note_date or cls.test_date

        return cls._set_vals_and_post(
            move=move,
            ref=ref,
            line_vals=line_vals,
            post=post
        )

    @classmethod
    def _create_debit_note(cls, inv, ref=None, debit_note_date=None, line_vals=None):
        move_debit_note_wiz = cls.env['account.debit.note'].with_context(
            active_model="account.move",
            active_ids=inv.ids
        ).create({
            'date': debit_note_date or cls.test_date,
            'reason': 'no reason',
            'copy_lines': True,
        })
        move_debit_note_wiz.create_debit()

        return cls._set_vals_and_post(move=inv.debit_note_ids[0], ref=ref, line_vals=line_vals)
