# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
from unittest.mock import patch, MagicMock

from odoo import tools
from odoo.tests import tagged
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyClientUser

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdi(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='it', edi_format_ref="l10n_it_edi.edi_fatturaPA"):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        # Company data ------
        cls.company = cls.company_data_2['company']
        cls.company.write({
            'vat': 'IT01234560157',
            'street': "1234 Test Street",
            'zip': "12345",
            'city': "Prova",
            'country_id': cls.env.ref('base.it').id,
            'l10n_it_codice_fiscale': '01234560157',
            'l10n_it_tax_system': "RF01",
        })
        cls.company.partner_id.write({
            'l10n_it_pa_index': "0803HR0"
        })

        cls.test_bank = cls.env['res.partner.bank'].create({
            'partner_id': cls.company.partner_id.id,
            'acc_number': 'IT1212341234123412341234123',
            'bank_name': 'BIG BANK',
            'bank_bic': 'BIGGBANQ',
        })

        # Partners
        cls.italian_partner_a = cls.env['res.partner'].create({
            'name': 'Alessi',
            'vat': 'IT00465840031',
            'l10n_it_codice_fiscale': '93026890017',
            'country_id': cls.env.ref('base.it').id,
            'street': 'Via Privata Alessi 6',
            'zip': '28887',
            'city': 'Milan',
            'company_id': False,
            'is_company': True,
        })

        cls.italian_partner_b = cls.env['res.partner'].create({
            'name': 'pa partner',
            'vat': 'IT06655971007',
            'l10n_it_codice_fiscale': '06655971007',
            'l10n_it_pa_index': '123456',
            'country_id': cls.env.ref('base.it').id,
            'street': 'Via Test PA',
            'zip': '32121',
            'city': 'PA Town',
            'is_company': True
        })

        cls.italian_partner_no_address_codice = cls.env['res.partner'].create({
            'name': 'Alessi',
            'l10n_it_codice_fiscale': '00465840031',
            'is_company': True,
        })

        cls.italian_partner_no_address_VAT = cls.env['res.partner'].create({
            'name': 'Alessi',
            'vat': 'IT00465840031',
            'is_company': True,
        })

        cls.american_partner = cls.env['res.partner'].create({
            'name': 'Alessi',
            'vat': '00465840031',
            'country_id': cls.env.ref('base.us').id,
            'is_company': True,
        })

        # We create this because we are unable to post without a proxy user existing
        cls.proxy_user = cls.env['account_edi_proxy_client.user'].create({
            'id_client': 'l10n_it_edi_test',
            'company_id': cls.company.id,
            'edi_identification': 'l10n_it_edi_test',
            'private_key': 'l10n_it_edi_test',
        })

        cls.default_tax = cls.env['account.tax'].with_company(cls.company).create({
            'name': "22%",
            'amount': 22.0,
            'amount_type': 'percent',
        })

        cls.module = 'l10n_it_edi'

    def _assert_export_invoice(self, invoice, filename):
        path = f'{self.module}/tests/export_xmls/{filename}'
        with tools.file_open(path, mode='rb') as fd:
            expected_tree = etree.fromstring(fd.read())
        invoice_etree = etree.fromstring(self.edi_format._l10n_it_edi_export_invoice_as_xml(invoice))
        self.assertXmlTreeEqual(invoice_etree, expected_tree)

    def _cleanup_etree(self, content, xpaths=None):
        xpaths = {
            **(xpaths or {}),
            '//FatturaElettronicaBody/Allegati': 'Allegati',
            '//DatiTrasmissione/ProgressivoInvio': 'ProgressivoInvio',
        }
        return self.with_applied_xpath(
            etree.fromstring(content),
            "".join([f"<xpath expr='{x}' position='replace'>{y}</xpath>" for x, y in xpaths.items()])
        )

    def _assert_import_invoice(self, filename, expected_values_list):
        path = f'{self.module}/tests/import_xmls/{filename}'
        with tools.file_open(path, mode='rb') as fd:
            import_content = fd.read()

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'raw': import_content,
        })
        invoices = self.company_data_2['default_journal_purchase']\
            .with_context(default_move_type='in_invoice')\
            ._create_document_from_attachment(attachment.ids)

        expected_invoice_values_list = []
        expected_invoice_line_ids_values_list = []
        for expected_values in expected_values_list:
            invoice_values = dict(expected_values)
            if 'invoice_line_ids' in invoice_values:
                expected_invoice_line_ids_values_list += invoice_values.pop('invoice_line_ids')
            expected_invoice_values_list.append(invoice_values)
        self.assertRecordValues(invoices, expected_invoice_values_list)
        if expected_invoice_line_ids_values_list:
            self.assertRecordValues(invoices.invoice_line_ids, expected_invoice_line_ids_values_list)

        return invoices
