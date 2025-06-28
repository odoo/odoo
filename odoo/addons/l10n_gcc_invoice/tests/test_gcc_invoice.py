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
        self.env['ir.config_parameter'].sudo().set_param('account.use_invoice_terms', True)

        gcc_countries = self.env.ref('base.gulf_cooperation_council').country_ids
        self.env.company.write({
            'country_id': gcc_countries[0].id,
            'invoice_terms': 'English Terms',
            'terms_type': 'plain',
        })
        # Add translation to invoice terms
        self.env.company.update_field_translations('invoice_terms', {'en_US': {'English Terms': 'English Terms'}, 'ar_001': {'English Terms': 'Arabic Terms'}})
        invoice = self.init_invoice('out_invoice', products=self.product_a)

        self.assertEqual(invoice.narration, Markup('<p>English Terms</p>'), 'Original narration not correct')
        self.assertEqual(invoice.with_context(lang='ar_001').narration, Markup('<p>Arabic Terms</p>'), 'Translation not loaded succesfully')
