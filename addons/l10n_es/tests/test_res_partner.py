from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nESTest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_es_company = cls.env['res.partner'].create({
            'name': 'ES Company',
            'vat': 'ESA12345674',
            'country_id': cls.env.ref('base.es').id,
        })

        cls.partner_es_dni = cls.env['res.partner'].create({
            'name': 'ES Individual (DNI)',
            'vat': 'ES47857909S',
            'country_id': cls.env.ref('base.es').id,
        })

        cls.partner_es_nie = cls.env['res.partner'].create({
            'name': 'ES Individual (NIE)',
            'vat': 'ESX1234567L',
            'country_id': cls.env.ref('base.es').id,
        })

    def test_is_company_es(self):
        self.assertTrue(
            self.partner_es_company.is_company,
            "ES Partner with a CIF-formatted VAT (letter + 7 digits + checksum) should be treated as a company.",
        )
        self.assertFalse(
            self.partner_es_dni.is_company,
            "ES Partner with a DNI-formatted VAT (8 digits + checksum letter) should be treated as an individual.",
        )
        self.assertFalse(
            self.partner_es_nie.is_company,
            "ES Partner with a NIE-formatted VAT (X/Y/Z + 7 digits + checksum letter) should be treated as an individual.",
        )


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nESIdTypesTest(TransactionCase):
    """ Covers `_l10n_es_edi_get_partner_info`, shared by SII and Veri*factu.

    IDType priority table (most reliable first): 02 NIF-IVA, 03 Pasaporte,
    04 Doc. oficial país de residencia, 05 Certificado de residencia, 06 Otro doc. probatorio.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.es = cls.env.ref('base.es')
        cls.be = cls.env.ref('base.be')  # EU member
        cls.us = cls.env.ref('base.us')  # non-EU

        cls.partner = cls.env['res.partner'].create({'name': 'ID Types Partner'})

    def _set_es_ids(self, passport=False, foreign_id=False, res_cert=False, other_id=False):
        self.partner.write({
            'l10n_es_passport': passport,
            'l10n_es_foreign_id': foreign_id,
            'l10n_es_res_cert': res_cert,
            'l10n_es_other_id': other_id,
        })

    def test_metadata_registered(self):
        metadata = self.env['res.partner']._get_all_additional_identifiers_metadata()
        for key in ('ES_PASSPORT', 'ES_FOREIGN_ID', 'ES_RES_CERT', 'ES_OTHER_ID'):
            self.assertIn(key, metadata)

    def test_es_partner_with_vat_uses_nif(self):
        """ Spanish partner with VAT: plain NIF, no IDOtro. """
        self.partner.write({'country_id': self.es.id, 'vat': 'ESF35999705'})
        info = self.partner._l10n_es_edi_get_partner_info()
        self.assertEqual(info.get('NIF'), 'F35999705')
        self.assertNotIn('IDOtro', info)

    def test_es_partner_error_1117_context_adds_idtype_07(self):
        """ Pre-existing '07' special case (error 1117), untouched by this task, must keep working. """
        self.partner.write({'country_id': self.es.id, 'vat': 'ESF35999705'})
        info = self.partner.with_context(error_1117=True)._l10n_es_edi_get_partner_info()
        self.assertEqual(info['IDOtro']['IDType'], '07')

    def test_eu_partner_with_vat_uses_02(self):
        self.partner.write({'country_id': self.be.id, 'vat': 'BE0477472701'})
        info = self.partner._l10n_es_edi_get_partner_info()
        self.assertEqual(info['IDOtro'], {'IDType': '02', 'ID': 'BE0477472701'})

    def test_eu_partner_without_vat_is_not_02(self):
        """ Regression guard: an EU partner with no VAT must not be miscoded as '02'
        (it now falls through to the extranjero/priority branch instead). """
        self.partner.write({'country_id': self.be.id, 'vat': False})
        info = self.partner._l10n_es_edi_get_partner_info()
        self.assertNotEqual(info['IDOtro'].get('IDType'), '02')
        self.assertEqual(info['IDOtro']['IDType'], '06')
        self.assertEqual(info['IDOtro']['ID'], 'NO_DISPONIBLE')

    def test_foreign_passport_only(self):
        self.partner.write({'country_id': self.us.id})
        self._set_es_ids(passport='X1234567')
        info = self.partner._l10n_es_edi_get_partner_info()
        self.assertEqual(info['IDOtro']['IDType'], '03')
        self.assertEqual(info['IDOtro']['ID'], 'X1234567')
        self.assertEqual(info['IDOtro']['CodigoPais'], 'US')

    def test_foreign_id_only(self):
        self.partner.write({'country_id': self.us.id})
        self._set_es_ids(foreign_id='FID-1')
        info = self.partner._l10n_es_edi_get_partner_info()
        self.assertEqual(info['IDOtro']['IDType'], '04')
        self.assertEqual(info['IDOtro']['ID'], 'FID-1')

    def test_residence_certificate_only(self):
        self.partner.write({'country_id': self.us.id})
        self._set_es_ids(res_cert='RESCERT-1')
        info = self.partner._l10n_es_edi_get_partner_info()
        self.assertEqual(info['IDOtro']['IDType'], '05')
        self.assertEqual(info['IDOtro']['ID'], 'RESCERT-1')

    def test_other_document_only(self):
        self.partner.write({'country_id': self.us.id})
        self._set_es_ids(other_id='OTHER-1')
        info = self.partner._l10n_es_edi_get_partner_info()
        self.assertEqual(info['IDOtro']['IDType'], '06')
        self.assertEqual(info['IDOtro']['ID'], 'OTHER-1')

    def test_priority_all_four_set_picks_passport(self):
        self.partner.write({'country_id': self.us.id})
        self._set_es_ids(passport='PASS-1', foreign_id='FID-1', res_cert='RESCERT-1', other_id='OTHER-1')
        info = self.partner._l10n_es_edi_get_partner_info()
        self.assertEqual(info['IDOtro']['IDType'], '03')
        self.assertEqual(info['IDOtro']['ID'], 'PASS-1')

    def test_priority_without_passport_picks_foreign_id(self):
        self.partner.write({'country_id': self.us.id})
        self._set_es_ids(foreign_id='FID-1', res_cert='RESCERT-1', other_id='OTHER-1')
        info = self.partner._l10n_es_edi_get_partner_info()
        self.assertEqual(info['IDOtro']['IDType'], '04')
        self.assertEqual(info['IDOtro']['ID'], 'FID-1')

    def test_priority_without_passport_or_foreign_id_picks_res_cert(self):
        self.partner.write({'country_id': self.us.id})
        self._set_es_ids(res_cert='RESCERT-1', other_id='OTHER-1')
        info = self.partner._l10n_es_edi_get_partner_info()
        self.assertEqual(info['IDOtro']['IDType'], '05')
        self.assertEqual(info['IDOtro']['ID'], 'RESCERT-1')

    def test_fallback_to_vat_when_no_custom_id_set(self):
        self.partner.write({'country_id': self.us.id, 'vat': 'US-123456'})
        info = self.partner._l10n_es_edi_get_partner_info()
        self.assertEqual(info['IDOtro']['IDType'], '04')
        self.assertEqual(info['IDOtro']['ID'], 'US-123456')

    def test_fallback_no_vat_no_country(self):
        self.partner.write({'country_id': False, 'vat': False})
        info = self.partner._l10n_es_edi_get_partner_info()
        self.assertEqual(info['IDOtro']['IDType'], '06')
        self.assertEqual(info['IDOtro']['ID'], 'NO_DISPONIBLE')
        self.assertNotIn('CodigoPais', info['IDOtro'])
