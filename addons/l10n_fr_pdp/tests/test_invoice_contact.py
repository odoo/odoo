from base64 import b64decode
from unittest.mock import patch

from lxml import etree

from odoo.tests import tagged
from odoo.tools import file_open

from .common import TestL10nFrPdpCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPdpInvoiceContact(TestL10nFrPdpCommon):

    def _create_invoice_contact(self, **values):
        return self.env['res.partner'].create({
            'name': 'Billing service',
            'parent_id': self.partner_a.id,
            'type': 'invoice',
            'country_id': self.partner_a.country_id.id,
            **values,
        })

    def test_invoice_contact_default_and_override(self):
        contact = self._create_invoice_contact()
        self.assertEqual(contact.peppol_eas, self.partner_a.peppol_eas)
        self.assertEqual(contact.peppol_endpoint, self.partner_a.peppol_endpoint)

        # The copied address is only an initial value. A parent edit or a VAT
        # recomputation must not remove the contact's own routing suffix.
        contact.peppol_endpoint = '334175221_PARIS'
        self.partner_a.peppol_endpoint = '334175221_HEADQUARTERS'
        contact._compute_peppol_eas()
        contact._compute_peppol_endpoint()
        contact.invalidate_recordset(['peppol_eas', 'peppol_endpoint'])
        self.assertEqual(contact.peppol_eas, '0225')
        self.assertEqual(contact.peppol_endpoint, '334175221_PARIS')

    def test_invoice_contact_export(self):
        contact = self._create_invoice_contact(peppol_eas='0225', peppol_endpoint='334175221_PARIS')
        invoice = self._create_french_invoice(partner_id=contact.id)
        invoice.action_post()
        for edi_format in ('ubl_21_fr', 'ubl_bis3'):
            with self.subTest(edi_format=edi_format):
                xml, errors = contact._get_edi_builder(edi_format)._export_invoice(invoice)
                self.assertFalse(errors)
                tree = etree.fromstring(xml)
                customer = tree.find('./{*}AccountingCustomerParty/{*}Party')
                endpoint = customer.find('./{*}EndpointID')
                self.assertEqual(endpoint.text, '334175221_PARIS')
                self.assertEqual(endpoint.get('schemeID'), '0225')
                self.assertEqual(customer.findtext('./{*}PartyTaxScheme/{*}CompanyID'), self.partner_a.vat)
                self.assertEqual(
                    tree.findtext('./{*}AccountingSupplierParty/{*}Party/{*}EndpointID'),
                    self.env.company.partner_id.peppol_endpoint,
                )

    def test_send_invoice_contacts(self):
        self.env.company.account_peppol_proxy_state = 'receiver'
        invoices = self.env['account.move']
        receivers = {'334175221_PARIS', '334175221_LYON'}
        for endpoint in sorted(receivers):
            contact = self._create_invoice_contact(peppol_eas='0225', peppol_endpoint=endpoint)
            invoices |= self._create_french_invoice(partner_id=contact.id)
        invoices.action_post()

        def verification_state(partner, endpoint, eas, edi_format):
            # Only the contacts are registered, so any validation of the parent
            # would prevent sending even if the final receiver were correct.
            return 'valid' if endpoint in receivers and eas == '0225' else 'not_valid'

        def send_documents(sender, invoices_data, edi_user, params):
            self.assertEqual(edi_user, self.proxy_user)
            self.assertEqual({doc['receiver'] for doc in params['documents']}, {f'0225:{endpoint}' for endpoint in receivers})
            for document in params['documents']:
                tree = etree.fromstring(b64decode(document['ubl']))
                endpoint = tree.findtext('./{*}AccountingCustomerParty/{*}Party/{*}EndpointID')
                self.assertEqual(document['receiver'], f'0225:{endpoint}')
            self.assertEqual(set(invoices_data), set(invoices))

        sender = self.env['account.move.send']
        with (
            patch.object(self.env.registry['res.partner'], '_get_peppol_verification_state', verification_state),
            patch.object(self.env.registry['account.move.send'], '_send_peppol_documents', autospec=True, side_effect=send_documents) as send_mock,
        ):
            # Exercise the sending wizard too: its checkbox and final validation
            # must check the contact, rather than its unregistered parent.
            wizard = self.create_send_and_print(invoices[:1], sending_methods=['peppol'])
            self.assertFalse(wizard._get_peppol_checkbox_addendum_disable_reason())
            invoices_data = {}
            for invoice in invoices:
                xml, errors = self.env['account.edi.xml.ubl_21_fr']._export_invoice(invoice)
                self.assertFalse(errors)
                invoices_data[invoice] = {
                    # Other installed EDI modules also consume these settings.
                    **sender._get_default_sending_settings(
                        invoice, sending_methods={'peppol'}, invoice_edi_format='ubl_21_fr', extra_edis={},
                    ),
                    'ubl_cii_xml_attachment_values': {'raw': xml, 'name': 'invoice.xml'},
                }
            sender._call_web_service_after_invoice_pdf_render(invoices_data)
            send_mock.assert_called_once()
        self.assertEqual(invoices.partner_id.commercial_partner_id, self.partner_a)

    def test_foreign_invoice_contact_keeps_peppol_address(self):
        self.env.company.account_peppol_proxy_state = 'receiver'
        contact = self._create_invoice_contact(
            country_id=self.env.ref('base.be').id,
            peppol_eas='0208',
            peppol_endpoint='0477472701',
        )
        invoice = self._create_french_invoice(partner_id=contact.id)
        invoice.action_post()

        def verification_state(partner, endpoint, eas, edi_format):
            return 'valid' if (endpoint, eas, edi_format) == ('0477472701', '0208', 'ubl_bis3') else 'not_valid'

        with (
            patch.object(self.env.registry['res.partner'], '_get_peppol_verification_state', verification_state),
            patch.object(self.env.registry['res.partner'], '_fetch_active_annuaire_lines') as annuaire_lookup,
        ):
            wizard = self.create_send_and_print(invoice, sending_methods=['peppol'])
            self.assertEqual(wizard.invoice_edi_format, 'ubl_bis3')
            self.assertFalse(wizard._get_peppol_checkbox_addendum_disable_reason())
            annuaire_lookup.assert_not_called()
        self.assertEqual(contact.peppol_endpoint, '0477472701')

    def test_import_invoice_contact(self):
        for endpoint in ('334175221_PARIS', '334175221_LYON'):
            contact = self._create_invoice_contact(peppol_eas='0225', peppol_endpoint=endpoint)
            with file_open('l10n_fr_pdp/tests/test_files/import/ubl_21_fr/invoice/fr/ubl_21_fr_in_invoice_establishment.xml', 'rb') as xml_file:
                tree = etree.fromstring(xml_file.read())
            supplier = tree.find('./{*}AccountingSupplierParty/{*}Party')
            supplier.find('./{*}EndpointID').text = endpoint
            supplier.find('./{*}PartyIdentification/{*}ID').text = self.partner_a.siret
            attachment = self.env['ir.attachment'].create({
                'name': 'invoice.xml',
                'mimetype': 'application/xml',
                'raw': etree.tostring(tree),
            })
            bill = self._import_invoice_as_attachment_on(attachment=attachment)
            self.assertEqual(bill.partner_id, contact)
            self.assertEqual(bill.commercial_partner_id, self.partner_a)
