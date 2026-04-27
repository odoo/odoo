from unittest.mock import patch

import os

from odoo.tests import tagged
from odoo.tools import misc
from .common import _check_with_xsd_patch, TestL10nClEdiCommon


@tagged('post_install_l10n', 'post_install', '-at_install', 'l10n_cl_fetchmail_iec')
@patch('odoo.tools.xml_utils._check_with_xsd', _check_with_xsd_patch)
class TestFetchmailServerIec(TestL10nClEdiCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        purchase_journal = cls.company_data['default_journal_purchase']
        purchase_journal.write({'l10n_latam_use_documents': True})
        sale_journal = cls.company_data['default_journal_sale']
        sale_journal.write({'l10n_cl_point_of_sale_type': 'online', 'l10n_latam_use_documents': True})

    def test_create_invoice_with_iec_from_attachment_gasoline(self):
        """Test recognition of specific fuel taxes on fetchmail import: gasoline only"""
        att_name = 'incoming_invoice_iec_35.xml'
        from_address = 'incoming_dte@test.com'
        att_content = misc.file_open(f'l10n_cl_edi/tests/fetchmail_dtes_iec/{att_name}', filter_ext=('.xml',)).read()
        moves = self.env['fetchmail.server']._create_document_from_attachment(att_content, att_name, from_address, self.company_data['company'].id)

        self.assertEqual(len(moves), 1)

        move = moves[0]
        self.assertRecordValues(move, [{
            'name': 'FAC 000001',
            'partner_id': self.partner_sii.id,
            'l10n_latam_document_number': '000001',
            'l10n_cl_dte_acceptation_status': 'received',
            'invoice_source_email': from_address,
            'company_id': self.company_data['company'].id,
            'amount_total': 13900,
            'amount_tax': 3900,
        }])
        self.assertEqual(move.journal_id.type, 'purchase')
        self.assertEqual(move.l10n_latam_document_type_id.code, '33')
        self.assertEqual(len(move.invoice_line_ids), 1)
        self.assertEqual(len(move.line_ids), 4)
        self.assertEqual(move.line_ids[2].tax_line_id.l10n_cl_sii_code, 35)

    def test_create_invoice_with_iec_from_attachment_diesel(self):
        """Test recognition of specific fuel taxes on fetchmail import: diesel only"""
        att_name = 'incoming_invoice_iec_28.xml'
        from_address = 'incoming_dte@test.com'
        att_content = misc.file_open(f'l10n_cl_edi/tests/fetchmail_dtes_iec/{att_name}', filter_ext=('.xml',)).read()
        moves = self.env['fetchmail.server']._create_document_from_attachment(att_content, att_name, from_address, self.company_data['company'].id)

        self.assertEqual(len(moves), 1)

        move = moves[0]
        self.assertRecordValues(move, [{
            'name': 'FAC 000001',
            'partner_id': self.partner_sii.id,
            'l10n_latam_document_number': '000001',
            'l10n_cl_dte_acceptation_status': 'received',
            'invoice_source_email': from_address,
            'company_id': self.company_data['company'].id,
            'amount_total': 12900,
            'amount_tax': 2900,
        }])
        self.assertEqual(move.journal_id.type, 'purchase')
        self.assertEqual(move.l10n_latam_document_type_id.code, '33')
        self.assertEqual(len(move.invoice_line_ids), 1)
        self.assertEqual(len(move.line_ids), 4)
        self.assertEqual(move.line_ids[2].tax_line_id.l10n_cl_sii_code, 28)

    def test_create_invoice_with_iec_from_attachment_gasoline_diesel(self):
        """Test recognition of specific fuel taxes on fetchmail import: gasoline and diesel"""
        att_name = 'incoming_invoice_iec_35_28.xml'
        from_address = 'incoming_dte@test.com'
        att_content = misc.file_open(f'l10n_cl_edi/tests/fetchmail_dtes_iec/{att_name}', filter_ext=('.xml',)).read()
        moves = self.env['fetchmail.server']._create_document_from_attachment(att_content, att_name, from_address, self.company_data['company'].id)

        self.assertEqual(len(moves), 1)

        move = moves[0]
        self.assertRecordValues(move, [{
            'name': 'FAC 000001',
            'partner_id': self.partner_sii.id,
            'l10n_latam_document_number': '000001',
            'l10n_cl_dte_acceptation_status': 'received',
            'invoice_source_email': from_address,
            'company_id': self.company_data['company'].id,
            'amount_total': 26800,
            'amount_tax': 6800,
        }])
        self.assertEqual(move.journal_id.type, 'purchase')
        self.assertEqual(move.l10n_latam_document_type_id.code, '33')
        self.assertEqual(len(move.invoice_line_ids), 2)
        self.assertEqual(len(move.line_ids), 6)
        self.assertEqual(move.line_ids[3].tax_line_id.l10n_cl_sii_code, 35)
        self.assertEqual(move.line_ids[4].tax_line_id.l10n_cl_sii_code, 28)
