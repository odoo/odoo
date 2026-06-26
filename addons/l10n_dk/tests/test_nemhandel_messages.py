from contextlib import contextmanager
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import tagged, freeze_time

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.l10n_dk.tests.common import (
    FILE_PATH,
    ID_CLIENT,
    INCOMING_MESSAGE_UUID,
    OUTGOING_MESSAGE_UUID,
    REFRESH_TOKEN,
    mock_nemhandel_documents_retrieval,
    mock_nemhandel_lookup_not_found,
    mock_nemhandel_lookup_success,
    mock_nemhandel_send_document,
)


@contextmanager
def _mock_send(valid_identifiers, error=False):
    with (
        mock_nemhandel_lookup_success(valid_identifiers),
        mock_nemhandel_send_document(),
        mock_nemhandel_documents_retrieval(error=error),
    ):
        yield


@freeze_time('2023-01-01')
@tagged('post_install_l10n', 'post_install', '-at_install')
class TestNemhandelMessage(TestAccountMoveSendCommon):

    @classmethod
    @TestAccountMoveSendCommon.setup_country('dk')
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_str('l10n_dk.edi.mode', 'test')

        cls.env.company.write({
            'street': 'Boomvej 42',
            'nemhandel_identifier_type': '0088',
            'nemhandel_identifier_value': '5798009811512',
            'vat': 'DK58403288',
            'l10n_dk_nemhandel_proxy_state': 'receiver',
        })

        edi_identification = cls.env['account_edi_proxy_client.user']._get_proxy_identification(cls.env.company, 'nemhandel')
        cls.private_key = cls.env['certificate.key'].create({
            'name': 'Test key Nemhandel',
            'content': cls.file_read(f'{FILE_PATH}/private_key.pem'),
        })
        cls.proxy_user = cls.env['account_edi_proxy_client.user'].create({
            'id_client': ID_CLIENT,
            'proxy_type': 'nemhandel',
            'edi_mode': 'test',
            'edi_identification': edi_identification,
            'private_key_id': cls.private_key.id,
            'refresh_token': REFRESH_TOKEN,
        })

        with (
            mock_nemhandel_lookup_success(['0184:12345666']),  # valid_partner
            mock_nemhandel_lookup_not_found(['0184:12345674']),  # invalid_partner
        ):
            cls.invalid_partner, cls.valid_partner = cls.env['res.partner'].create([{
                'name': 'Wintermute',
                'city': 'Copenhagen',
                'country_id': cls.env.ref('base.dk').id,
                'invoice_sending_method': 'nemhandel',
                'vat': 'DK12345674',
            }, {
                'name': 'Molly',
                'street': 'Arfvej 7',
                'city': 'Copenhagen',
                'email': 'Namur@company.com',
                'country_id': cls.env.ref('base.dk').id,
                'invoice_sending_method': 'nemhandel',
                'vat': 'DK12345666',
            }])

        cls.env['res.partner.bank'].create({
            'account_number': '0144748555',
            'partner_id': cls.env.company.partner_id.id,
            'allow_out_payment': True,
        })

    def create_move(self, partner, company=None):
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': (company or self.env.company).id,
            'partner_id': partner.id,
            'date': '2023-01-01',
            'ref': 'Test reference',
            'invoice_line_ids': [
                Command.create({
                    'name': 'line 1',
                    'product_id': self.product_a.id,
                }),
                Command.create({
                    'name': 'line 2',
                    'product_id': self.product_a.id,
                }),
            ],
        })

    def test_nemhandel_attachment_placeholders(self):
        move = self.create_move(self.valid_partner)
        move.action_post()

        with mock_nemhandel_lookup_success(['0184:12345666']):
            wizard = self.create_send_and_print(move, sending_methods=['email', 'nemhandel'])
            self.assertEqual(wizard.invoice_edi_format, 'oioubl_21')

            # the ubl xml placeholder should be generated
            self._assert_mail_attachments_widget(wizard, [
                {
                    'mimetype': 'application/pdf',
                    'name': 'INV_2023_00001.pdf',
                    'placeholder': True,
                },
                {
                    'mimetype': 'application/xml',
                    'name': 'INV_2023_00001_oioubl_21.xml',
                    'placeholder': True,
                },
            ])

            wizard.sending_methods = ['nemhandel']
            with mock_nemhandel_send_document():
                wizard.action_send_and_print()
        self.assertEqual(self._get_mail_message(move).preview, 'The document has been sent to the Nemhandel Access Point for processing')

    def test_send_nemhandel_alerts_not_valid_partner(self):
        move = self.create_move(self.invalid_partner)
        move.action_post()
        with mock_nemhandel_lookup_not_found(['0184:12345674']):  # not on nemhandel at all
            wizard = self.env['account.move.send.wizard'].create({
                'move_id': move.id,
            })
            self.assertEqual(self.invalid_partner.nemhandel_verification_state, 'not_valid')
            self.assertFalse(wizard.sending_methods)  # nemhandel is not there at all
            self.assertFalse(wizard.alerts)  # there is no alerts

    def test_resend_error_nemhandel_message(self):
        # should be able to resend error invoices
        move = self.create_move(self.valid_partner)
        move.action_post()

        with _mock_send(['0184:12345666'], error=True):
            wizard = self.create_send_and_print(move, default=True)
            self.assertEqual(wizard.invoice_edi_format, 'oioubl_21')
            self.assertTrue(wizard.sending_methods and 'nemhandel' in wizard.sending_methods)
            wizard.action_send_and_print()

            self.env['account_edi_proxy_client.user']._cron_nemhandel_get_message_status()
            self.assertRecordValues(move, [{'nemhandel_move_state': 'error', 'nemhandel_message_uuid': OUTGOING_MESSAGE_UUID}])

        # we can't send the ubl document again unless we regenerate the pdf
        move.invoice_pdf_report_id.unlink()
        with _mock_send(['0184:12345666']):
            wizard = self.create_send_and_print(move, default=True)
            self.assertEqual(wizard.invoice_edi_format, 'oioubl_21')
            self.assertTrue(wizard.sending_methods and 'nemhandel' in wizard.sending_methods)

            wizard.action_send_and_print()

            self.env['account_edi_proxy_client.user']._cron_nemhandel_get_message_status()
        self.assertEqual(move.nemhandel_move_state, 'done')

    def test_nemhandel_send_success_message(self):
        # should be able to send valid invoices correctly
        # attachment should be generated
        # nemhandel_move_state should be set to done
        move = self.create_move(self.valid_partner)
        move.action_post()

        with _mock_send(['0184:12345666']):
            wizard = self.create_send_and_print(move, default=True)
            self.assertEqual(wizard.invoice_edi_format, 'oioubl_21')
            self.assertTrue(wizard.sending_methods and 'nemhandel' in wizard.sending_methods)

            wizard.action_send_and_print()

            self.env['account_edi_proxy_client.user']._cron_nemhandel_get_message_status()
        self.assertRecordValues(
            move,
            [{
                'nemhandel_move_state': 'done',
                'nemhandel_message_uuid': OUTGOING_MESSAGE_UUID,
            }],
        )
        self.assertTrue(bool(move.ubl_cii_xml_id))

    def test_nemhandel_send_invalid_edi_user(self):
        # an invalid edi user should not be able to send invoices via nemhandel
        self.env.company.l10n_dk_nemhandel_proxy_state = 'rejected'

        move = self.create_move(self.valid_partner)
        move.action_post()

        with mock_nemhandel_lookup_success(['0184:12345666']):
            wizard = self.create_send_and_print(move, default=True)
            self.assertTrue('nemhandel' not in wizard.sending_method_checkboxes)

    def test_receive_error_nemhandel(self):
        # an error nemhandel message should be created
        with mock_nemhandel_documents_retrieval(error=True):
            self.env['account_edi_proxy_client.user']._cron_nemhandel_get_new_documents()

        move = self.env['account.move'].search([('nemhandel_message_uuid', '=', INCOMING_MESSAGE_UUID)])
        self.assertRecordValues(move, [{'nemhandel_move_state': 'error', 'move_type': 'in_invoice'}])

    def test_receive_success_nemhandel(self):
        # a correct move should be created
        with mock_nemhandel_documents_retrieval():
            self.env['account_edi_proxy_client.user']._cron_nemhandel_get_new_documents()

        move = self.env['account.move'].search([('nemhandel_message_uuid', '=', INCOMING_MESSAGE_UUID)])
        self.assertRecordValues(move, [{'nemhandel_move_state': 'done', 'move_type': 'in_invoice'}])

    def test_validate_partner_nemhandel(self):
        new_partner = self.env['res.partner'].create({
            'name': 'Deanna Troi',
            'city': 'Copenhagen',
            'country_id': self.env.ref('base.dk').id,
            'invoice_sending_method': 'nemhandel',

        })
        self.assertRecordValues(
            new_partner,
            [{
                'nemhandel_verification_state': False,
                'nemhandel_identifier_type': '0184',
                'nemhandel_identifier_value': False,
            }],
        )
        with mock_nemhandel_lookup_success(['0088:5798009811512']):
            new_partner.write({
                'nemhandel_identifier_type': '0088',
                'nemhandel_identifier_value': '5798009811512',
            })
            self.assertEqual(new_partner.nemhandel_verification_state, 'valid')  # should validate automatically

        with mock_nemhandel_lookup_not_found(['0184:12345674']):  # not on nemhandel
            new_partner.write({
                'nemhandel_identifier_type': '0184',
                'nemhandel_identifier_value': '12345674',
            })
            self.assertEqual(new_partner.nemhandel_verification_state, 'not_valid')

    def test_nemhandel_edi_formats(self):
        self.valid_partner.invoice_sending_method = 'nemhandel'
        with self.assertRaises(UserError):
            self.valid_partner.invoice_edi_format = 'ubl_bis3'

        self.valid_partner.invoice_sending_method = 'email'
        self.valid_partner.invoice_edi_format = 'ubl_bis3'

    def test_nemhandel_silent_error_while_creating_xml(self):
        """When in multi/async mode, the generation of XML can fail silently (without raising).
        This needs to be reflected as an error and put the move in Nemhandel Error state.
        """
        def mocked_export_invoice_constraints(self, invoice, vals):
            return {'test_error_key': 'test_error_description'}

        self.valid_partner.invoice_edi_format = 'oioubl_21'
        move_1 = self.create_move(self.valid_partner)
        move_2 = self.create_move(self.valid_partner)
        (move_1 + move_2).action_post()

        with mock_nemhandel_lookup_success(['0184:12345666']):
            wizard = self.create_send_and_print(move_1 + move_2)
        with patch(
            'odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_20.AccountEdiXmlUBL20._export_invoice_constraints',
            mocked_export_invoice_constraints
        ), self.enter_registry_test_mode(), _mock_send(['0184:12345666']):
            wizard.action_send_and_print()
            self.env.ref('account.ir_cron_account_move_send').method_direct_trigger()
        self.assertEqual(move_1.nemhandel_move_state, 'error')
