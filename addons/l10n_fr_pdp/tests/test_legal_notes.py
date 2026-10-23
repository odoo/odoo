# -*- coding: utf-8 -*-

from unittest.mock import patch

from lxml import etree

from odoo.tests import tagged

from odoo.addons.l10n_fr_pdp.tests.common import TestL10nFrPdpCommon

STUDIO_FIELDS = (
    'x_studio_peppol_company_legal_form',
    'x_studio_peppol_company_share_capital',
    'x_studio_peppol_company_rcs_city',
)


def _localname(node):
    return etree.QName(node).localname


def _texts(xml_bytes, local_name, ancestor=None):
    root = etree.fromstring(xml_bytes)
    texts = []
    nodes = root.iter()
    if ancestor:
        nodes = []
        for party in root.iter():
            if _localname(party) == ancestor:
                nodes.extend(party.iter())
    for node in nodes:
        if _localname(node) == local_name and node.text:
            texts.append(node.text)
    return texts


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestLegalNotesStudio(TestL10nFrPdpCommon):

    @classmethod
    def setUpClass(cls):
        try:
            from odoo.addons.l10n_fr_siret.models.res_partner import Partner as FrPartner
        except ImportError:
            super().setUpClass()
            return
        with patch.object(FrPartner, '_inverse_siret', lambda self: None):
            super().setUpClass()

    def _fill_legal_notes(self, legal_form='SAS', capital=50000.0, city='Paris'):
        self.company.write({
            'x_studio_peppol_company_legal_form': legal_form,
            'x_studio_peppol_company_share_capital': capital,
            'x_studio_peppol_company_rcs_city': city,
        })

    def test_studio_fields_are_manual_without_xmlid(self):
        for name in STUDIO_FIELDS:
            field = self.env['ir.model.fields'].search([
                ('model', '=', 'res.company'),
                ('name', '=', name),
            ], limit=1)
            self.assertTrue(field, name)
            self.assertEqual(field.state, 'manual')
            xmlid = self.env['ir.model.data'].search([
                ('model', '=', 'ir.model.fields'),
                ('res_id', '=', field.id),
            ])
            self.assertFalse(xmlid)

    def test_settings_write_studio_fields(self):
        self.env['res.config.settings'].create({
            'company_id': self.company.id,
            'l10n_fr_pdp_legal_form': 'SAS',
            'l10n_fr_pdp_share_capital': 10000.0,
            'l10n_fr_pdp_rcs_city': 'Lyon',
        })
        self.assertEqual(self.company.x_studio_peppol_company_legal_form, 'SAS')
        self.assertEqual(self.company.x_studio_peppol_company_share_capital, 10000.0)
        self.assertEqual(self.company.x_studio_peppol_company_rcs_city, 'Lyon')

    def test_notes_absent_when_fields_empty(self):
        self._fill_legal_notes(legal_form=False, capital=0.0, city=False)
        notes = self._create_french_invoice()._l10n_fr_pdp_get_default_notes()
        self.assertNotIn('REG', notes)
        self.assertNotIn('ABL', notes)
        self.assertIn('PMT', notes)
        self.assertNotIn('AAI', notes)

    def test_reg_requires_form_and_capital(self):
        invoice = self._create_french_invoice()
        self._fill_legal_notes(legal_form='SAS', capital=0.0, city=False)
        self.assertNotIn('REG', invoice._l10n_fr_pdp_get_default_notes())
        self._fill_legal_notes(legal_form=False, capital=50000.0, city='Paris')
        notes = invoice._l10n_fr_pdp_get_default_notes()
        self.assertNotIn('REG', notes)
        self.assertIn('ABL', notes)
        self.assertIn('Paris', notes['ABL'])

    def test_notes_and_ubl_bt33(self):
        self._fill_legal_notes()
        invoice = self._create_french_invoice()
        notes = invoice._l10n_fr_pdp_get_default_notes()
        siren = self.company.partner_id._l10n_fr_pdp_get_siren()
        self.assertIn('SAS', notes['REG'])
        self.assertIn('50 000', notes['REG'])
        self.assertIn('EUR', notes['REG'])
        self.assertIn('RCS Paris', notes['ABL'])
        self.assertIn(siren, notes['ABL'])
        self.assertNotIn('AAI', notes)

        invoice.action_post()
        xml_bytes, errors = self.env['account.edi.xml.ubl_21_fr']._export_invoice(invoice)
        self.assertFalse(errors, errors)
        reg_notes = [text for text in _texts(xml_bytes, 'Note') if '#REG#' in text]
        abl_notes = [text for text in _texts(xml_bytes, 'Note') if '#ABL#' in text]
        self.assertEqual(len(reg_notes), 1)
        self.assertEqual(len(abl_notes), 1)
        supplier_forms = _texts(xml_bytes, 'CompanyLegalForm', ancestor='AccountingSupplierParty')
        customer_forms = _texts(xml_bytes, 'CompanyLegalForm', ancestor='AccountingCustomerParty')
        self.assertEqual(supplier_forms, [notes['REG']])
        self.assertFalse(customer_forms)

    def test_ubl_deduplicates_existing_reg(self):
        self._fill_legal_notes()
        invoice = self._create_french_invoice(narration='#REG#already stated')
        invoice.action_post()
        xml_bytes, _errors = self.env['account.edi.xml.ubl_21_fr']._export_invoice(invoice)
        reg_notes = [text for text in _texts(xml_bytes, 'Note') if '#REG#' in text]
        self.assertEqual(reg_notes, ['#REG#already stated'])
        self.assertEqual(len([text for text in _texts(xml_bytes, 'Note') if '#ABL#' in text]), 1)

    def test_cii_reg_and_abl_subject_codes(self):
        self._fill_legal_notes()
        invoice = self._create_french_invoice()
        invoice.action_post()
        xml_bytes, _errors = self.env['account.edi.xml.cii']._export_invoice(invoice)
        subjects = _texts(xml_bytes, 'SubjectCode')
        self.assertEqual(subjects.count('REG'), 1)
        self.assertEqual(subjects.count('ABL'), 1)
        self.assertEqual(subjects.count('PMT'), 1)
        self.assertNotIn('AAI', subjects)
        self.assertFalse(_texts(xml_bytes, 'CompanyLegalForm'))

    def test_cii_deduplicates_existing_reg(self):
        self._fill_legal_notes()
        invoice = self._create_french_invoice(narration='#REG#already stated')
        invoice.action_post()
        xml_bytes, _errors = self.env['account.edi.xml.cii']._export_invoice(invoice)
        subjects = _texts(xml_bytes, 'SubjectCode')
        self.assertNotIn('REG', subjects)
        self.assertEqual(subjects.count('ABL'), 1)
        self.assertEqual(xml_bytes.decode().count('#REG#'), 1)
