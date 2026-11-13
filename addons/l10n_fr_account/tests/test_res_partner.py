# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestResPartner(BaseCommon):

    def test_peppol_endpoint_from_vat(self):
        if self.env['ir.module.module']._get('account_edi_ubl_cii').state != 'installed':
            self.skipTest("'account_edi_ubl_cii' is not installed")

        partner = self.env['res.partner'].create({
            'name': 'French partner with only a VAT number',
            'country_id': self.env.ref('base.fr').id,
            'vat': 'FR23334175221',
        })
        self.assertRecordValues(partner, [{
            'peppol_eas': '0225',
            'peppol_endpoint': '334175221',
        }])

        partner.vat = 'FR35562153452'
        self.assertRecordValues(partner, [{
            'peppol_eas': '0225',
            'peppol_endpoint': '562153452',
        }])
