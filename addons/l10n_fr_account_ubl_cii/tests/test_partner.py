from odoo.tests import tagged

from .common import TestL10nFrAccountUblCiiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nFrAccountUblCiiCommonPartner(TestL10nFrAccountUblCiiCommon):

    def test_compute_pdp_identifier(self):
        partner = self.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER 2',
            'street': 'Rue Fabricy, 16',
            'zip': '59000',
            'city': 'Lille',
            'country_id': self.env.ref('base.fr').id,
            'phone': '+33 1 23 45 67 89',
            'vat': 'FR23334175221',
            'siret': '96851575905877',
            'invoice_edi_format': 'ubl_21_fr',
        })
        self.assertRecordValues(partner, [{
            'peppol_endpoint': '968515759',
            'peppol_eas': '0225',
        }])

        partner = self.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER 2',
            'street': 'Rue Fabricy, 16',
            'zip': '59000',
            'city': 'Lille',
            'country_id': self.env.ref('base.fr').id,
            'phone': '+33 1 23 45 67 89',
            'vat': 'FR23334175221',
            'company_registry': '96851575905877',
            'invoice_edi_format': 'ubl_21_fr',
        })
        self.assertRecordValues(partner, [{
            'peppol_endpoint': '968515759',
            'peppol_eas': '0225',
        }])

        partner = self.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER 2',
            'street': 'Rue Fabricy, 16',
            'zip': '59000',
            'city': 'Lille',
            'country_id': self.env.ref('base.fr').id,
            'phone': '+33 1 23 45 67 89',
            'vat': 'FR23334175221',
            'siret': '968515759',
            'invoice_edi_format': 'ubl_21_fr',
        })
        self.assertRecordValues(partner, [{
            'peppol_endpoint': '968515759',
            'peppol_eas': '0225',
        }])

        partner = self.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER 2',
            'street': 'Rue Fabricy, 16',
            'zip': '59000',
            'city': 'Lille',
            'country_id': self.env.ref('base.fr').id,
            'phone': '+33 1 23 45 67 89',
            'vat': 'FR23334175221',
            'company_registry': '968515759',
            'invoice_edi_format': 'ubl_21_fr',
        })
        self.assertRecordValues(partner, [{
            'peppol_endpoint': '968515759',
            'peppol_eas': '0225',
        }])
