from odoo.tests import tagged

from .common import TestEsEdiTbaiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTbaiRecipientIdTypes(TestEsEdiTbaiCommon):
    """ TBAI reimplements the ID-type priority logic independently of `_l10n_es_edi_get_partner_info`
    (used by SII/Veri*factu) in `_get_recipient_values`. Same matrix, kept in sync manually - test both. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_model = cls.env['l10n_es_edi_tbai.document']
        cls.us = cls.env.ref('base.us')  # non-EU
        cls.partner = cls.env['res.partner'].create({'name': 'TBAI ID Types Partner'})

    def _set_es_ids(self, passport=False, foreign_id=False, res_cert=False, other_id=False):
        self.partner.write({
            'l10n_es_passport': passport,
            'l10n_es_foreign_id': foreign_id,
            'l10n_es_res_cert': res_cert,
            'l10n_es_other_id': other_id,
        })

    def test_es_partner_with_nif(self):
        self.partner.write({'country_id': self.env.ref('base.es').id, 'vat': 'ESF35999705'})
        values = self.doc_model._get_recipient_values(self.partner)['recipient']
        self.assertEqual(values['nif'], 'F35999705')
        self.assertNotIn('alt_id_type', values)

    def test_eu_partner_with_vat_uses_02(self):
        self.partner.write({'country_id': self.env.ref('base.be').id, 'vat': 'BE0477472701'})
        values = self.doc_model._get_recipient_values(self.partner)['recipient']
        self.assertEqual(values['alt_id_type'], '02')
        self.assertEqual(values['alt_id_number'], 'BE0477472701')

    def test_eu_partner_without_vat_is_not_02(self):
        """ Regression guard: EU country with no VAT must not be miscoded as '02'. """
        self.partner.write({'country_id': self.env.ref('base.be').id, 'vat': False})
        values = self.doc_model._get_recipient_values(self.partner)['recipient']
        self.assertNotEqual(values.get('alt_id_type'), '02')
        self.assertEqual(values['alt_id_type'], '06')
        self.assertEqual(values['alt_id_number'], 'NO_DISPONIBLE')

    def test_passport_priority(self):
        self.partner.write({'country_id': self.us.id})
        self._set_es_ids(passport='PASS-1', foreign_id='FID-1', res_cert='RESCERT-1', other_id='OTHER-1')
        values = self.doc_model._get_recipient_values(self.partner)['recipient']
        self.assertEqual(values['alt_id_type'], '03')
        self.assertEqual(values['alt_id_number'], 'PASS-1')
        self.assertEqual(values['alt_id_country'], 'US')

    def test_foreign_id_priority_when_no_passport(self):
        self.partner.write({'country_id': self.us.id})
        self._set_es_ids(foreign_id='FID-1', res_cert='RESCERT-1', other_id='OTHER-1')
        values = self.doc_model._get_recipient_values(self.partner)['recipient']
        self.assertEqual(values['alt_id_type'], '04')
        self.assertEqual(values['alt_id_number'], 'FID-1')

    def test_res_cert_priority_when_no_passport_or_foreign_id(self):
        self.partner.write({'country_id': self.us.id})
        self._set_es_ids(res_cert='RESCERT-1', other_id='OTHER-1')
        values = self.doc_model._get_recipient_values(self.partner)['recipient']
        self.assertEqual(values['alt_id_type'], '05')
        self.assertEqual(values['alt_id_number'], 'RESCERT-1')

    def test_other_id_only(self):
        self.partner.write({'country_id': self.us.id})
        self._set_es_ids(other_id='OTHER-1')
        values = self.doc_model._get_recipient_values(self.partner)['recipient']
        self.assertEqual(values['alt_id_type'], '06')
        self.assertEqual(values['alt_id_number'], 'OTHER-1')

    def test_fallback_to_vat(self):
        self.partner.write({'country_id': self.us.id, 'vat': 'US-999'})
        values = self.doc_model._get_recipient_values(self.partner)['recipient']
        self.assertEqual(values['alt_id_type'], '04')
        self.assertEqual(values['alt_id_number'], 'US-999')

    def test_fallback_no_vat_no_country(self):
        self.partner.write({'country_id': False, 'vat': False})
        values = self.doc_model._get_recipient_values(self.partner)['recipient']
        self.assertEqual(values['alt_id_type'], '06')
        self.assertEqual(values['alt_id_number'], 'NO_DISPONIBLE')
        self.assertIsNone(values.get('alt_id_country'))

    def test_simplified_invoice_without_vat_skips_recipient(self):
        """ Simplified invoices only carry recipient data when the partner has a VAT. """
        self.partner.write({'country_id': self.us.id, 'vat': False})
        self.assertEqual(self.doc_model._get_recipient_values(self.partner, is_simplified=True), {})
