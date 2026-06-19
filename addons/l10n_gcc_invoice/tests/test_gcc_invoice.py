# -*- coding: utf-8 -*-

from markupsafe import Markup

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestGccInvoice(AccountTestInvoicingCommon):

    def test_invoice_narration_translation(self):
        ''' The narration field should be copied translations included'''
        # Activate second lang and parameter needed to display invoice terms
        self.env['res.lang']._activate_lang('ar_001')
        self.env['ir.config_parameter'].sudo().set_bool('account.use_invoice_terms', True)
        gcc_countries = self.env.ref('base.gulf_cooperation_council').country_ids
        self.env.company.write({
            'country_id': gcc_countries[0].id,
            'invoice_terms': 'English Terms',
            'terms_type': 'plain',
        })
        # Add translation to invoice terms
        self.env.company.update_field_translations('invoice_terms', {'en_US': {'English Terms': 'English Terms'}, 'ar_001': {'English Terms': 'Arabic Terms'}})
        # Create invoice with English partner (default)
        invoice_en = self.init_invoice('out_invoice', products=self.product_a)
        self.assertEqual(invoice_en.narration, Markup('<p>English Terms</p>'), 'Invoice narration should show English terms for English partner')
        # Create invoice with Arabic partner
        ar_partner = self.env['res.partner'].create({'name': 'Arabic Partner', 'lang': 'ar_001'})
        invoice_ar = self.init_invoice('out_invoice', products=self.product_a, partner=ar_partner)
        self.assertEqual(invoice_ar.narration, Markup('<p>Arabic Terms</p>'), 'Invoice narration should show Arabic terms for Arabic partner')
