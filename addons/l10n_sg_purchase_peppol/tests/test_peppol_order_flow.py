from datetime import datetime
from unittest.mock import patch

from lxml import etree

from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, freeze_time, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_sg_purchase_peppol.models.purchase_order import PEPPOL_ORDER_DOCUMENT_ID, PurchaseOrder


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPeppolPurchaseOrderFlow(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Programmatic PEPPOL setup so tests run on a fresh DB (no manual registration).
        cls.env.company.write({
            'routing_scheme': '0208',
            'routing_endpoint': '0477472701',
            'account_peppol_proxy_state': 'sender',
        })
        edi_identification = cls.env['account_edi_proxy_client.user']._get_proxy_identification(
            cls.env.company, 'peppol'
        )
        cls.private_key = cls.env['certificate.key'].create({
            'name': 'Test key PEPPOL',
            'content': cls.file_read('account_peppol/tests/assets/private_key.pem'),
        })
        cls.env['account_edi_proxy_client.user'].create({
            'id_client': 'test-peppol-purchase-order-flow',
            'company_id': cls.env.company.id,
            'proxy_type': 'peppol',
            'edi_mode': 'test',
            'edi_identification': edi_identification,
            'private_key_id': cls.private_key.id,
            'refresh_token': 'test-refresh-token',
        })

        # Vendor (receiver of the order) must have Peppol identifier for sending.
        cls.partner_a.vat = 'NL123456782B90'
        cls.partner_a.routing_scheme = '0208'
        cls.partner_a.routing_endpoint = '0239843189'  # Valid format for EAS 0208 (Belgium)
        cls.partner_a.email = 'vendor_a@example.com'
        # Pretend the vendor has been looked up on Peppol and can receive orders (no HTTP in tests).
        cls.partner_a.with_company(cls.env.company).write({
            'peppol_verification_state': 'valid',
            'peppol_supported_documents': [f'{PEPPOL_ORDER_DOCUMENT_ID}::2.1'],
        })

        cls.env.company.vat = 'BE0477472701'
        cls.po = cls.env['purchase.order'].create({
            'name': 'Test PO',
            'partner_id': cls.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': cls.product_a.id,
                'name': 'Product A',
                'product_qty': 10.0,
                'price_unit': 50.0,
            })],
        })

    def test_send_initial_order(self):
        """Test sending initial order creates a transaction."""
        po = self.po
        self.assertEqual(po.state, 'draft')
        self.assertTrue(po.l10n_sg_peppol_can_send_order)
        self.assertEqual(len(po.l10n_sg_peppol_order_tx_ids), 0)

        po._l10n_sg_peppol_send_order()
        self.assertFalse(po.l10n_sg_peppol_can_send_order)
        self.assertEqual(len(po.l10n_sg_peppol_order_tx_ids), 1)

        tx = po.l10n_sg_peppol_order_tx_ids[:1]
        self.assertEqual(tx.state, 'sent')
        self.assertEqual(tx.document_type, 'order')
        self.assertEqual(tx.sequence, 0)

    def test_receive_order_accept(self):
        """Test receiving order accept confirms the order and marks tx accepted."""
        po = self.po
        po._l10n_sg_peppol_send_order()

        po.handle_order_response_advanced(False, 'AP')
        self.assertEqual(po.state, 'purchase')

        tx = po.l10n_sg_peppol_order_tx_ids.filtered(lambda t: t.document_type == 'order')[:1]
        self.assertEqual(tx.state, 'accepted')

        messages = po.message_ids.filtered(lambda m: 'Order is accepted by the seller' in m.body)
        self.assertTrue(messages)

    def test_receive_order_reject(self):
        """Test receiving order reject cancels the order and marks tx rejected."""
        po = self.po
        po._l10n_sg_peppol_send_order()

        po.handle_order_response_advanced(False, 'RE')
        self.assertEqual(po.state, 'cancel')

        tx = po.l10n_sg_peppol_order_tx_ids.filtered(lambda t: t.document_type == 'order')[:1]
        self.assertEqual(tx.state, 'rejected')

        messages = po.message_ids.filtered(lambda m: 'Order is rejected by the seller' in m.body)
        self.assertTrue(messages)

    def test_send_order_change(self):
        """Test sending order change creates a new order_change transaction."""
        po = self.po
        po._l10n_sg_peppol_send_order()
        po.handle_order_response_advanced(False, 'AP')
        self.assertTrue(po.l10n_sg_peppol_can_send_order_change)

        initial_tx_count = len(po.l10n_sg_peppol_order_tx_ids)
        po.action_send_order_change()
        self.assertEqual(len(po.l10n_sg_peppol_order_tx_ids), initial_tx_count + 1)
        self.assertFalse(po.l10n_sg_peppol_can_send_order_change)

        change_tx = po.l10n_sg_peppol_order_tx_ids.filtered(lambda t: t.document_type == 'order_change')[:1]
        self.assertEqual(change_tx.state, 'sent')
        self.assertEqual(change_tx.sequence, 1)
        self.assertTrue(change_tx.order_change_ref)

    def test_receive_change_accept(self):
        """Test receiving order change accept marks change tx accepted."""
        po = self.po
        po._l10n_sg_peppol_send_order()
        po.handle_order_response_advanced(False, 'AP')
        po.action_send_order_change()

        change_tx = po.l10n_sg_peppol_order_tx_ids.filtered(lambda t: t.document_type == 'order_change')[:1]
        po.handle_order_response_advanced(change_tx.order_change_ref, 'AP')

        self.assertEqual(change_tx.state, 'accepted')
        self.assertTrue(po.l10n_sg_peppol_can_send_order_change)
        messages = po.message_ids.filtered(lambda m: 'Order change request is accepted by the seller' in m.body)
        self.assertTrue(messages)

    def test_receive_change_reject(self):
        """Test receiving order change reject reverts the order to last accepted tx."""
        po = self.po
        po._l10n_sg_peppol_send_order()
        po.handle_order_response_advanced(False, 'AP')

        po.order_line[:1].product_qty = 12.0
        po.action_send_order_change()
        change_tx = po.l10n_sg_peppol_order_tx_ids.filtered(lambda t: t.document_type == 'order_change')[:1]
        po.handle_order_response_advanced(change_tx.order_change_ref, 'RE')

        self.assertEqual(change_tx.state, 'rejected')
        self.assertEqual(po.order_line[:1].product_qty, 10.0)
        messages = po.message_ids.filtered(lambda m: 'Order change request is rejected by the seller' in m.body)
        self.assertTrue(messages)

    def test_send_order_cancel(self):
        """Test sending order cancel creates an order_cancel transaction."""
        po = self.po
        po._l10n_sg_peppol_send_order()
        po.handle_order_response_advanced(False, 'AP')
        self.assertTrue(po.l10n_sg_peppol_can_send_order_cancel)
        initial_tx_count = len(po.l10n_sg_peppol_order_tx_ids)

        po.action_send_order_cancel()

        self.assertEqual(len(po.l10n_sg_peppol_order_tx_ids), initial_tx_count + 1)
        self.assertFalse(po.l10n_sg_peppol_can_send_order_cancel)
        cancel_tx = po.l10n_sg_peppol_order_tx_ids.filtered(
            lambda t: t.document_type == 'order_cancel'
        ).sorted()[:1]
        self.assertEqual(cancel_tx.state, 'sent')

    def test_receive_cancel_accept(self):
        """Test receiving cancellation accept c  ancels the order."""
        po = self.po
        po._l10n_sg_peppol_send_order()
        po.handle_order_response_advanced(False, 'AP')
        po.action_send_order_cancel()
        po.handle_order_response_advanced(False, 'RE')

        cancel_tx = po.l10n_sg_peppol_order_tx_ids.filtered(
            lambda t: t.document_type == 'order_cancel'
        ).sorted()[:1]
        self.assertEqual(po.state, 'cancel')
        self.assertEqual(cancel_tx.state, 'accepted')

    def test_receive_cancel_reject(self):
        """Test receiving cancellation reject keeps the order confirmed."""
        po = self.po
        po._l10n_sg_peppol_send_order()
        po.handle_order_response_advanced(False, 'AP')
        po.action_send_order_cancel()
        po.handle_order_response_advanced(False, 'AP')

        cancel_tx = po.l10n_sg_peppol_order_tx_ids.filtered(
            lambda t: t.document_type == 'order_cancel'
        ).sorted()[:1]
        self.assertEqual(po.state, 'purchase')
        self.assertEqual(cancel_tx.state, 'rejected')

    def test_invalid_event(self):
        """Test invalid response code raises ValidationError."""
        po = self.po
        po._l10n_sg_peppol_send_order()
        with self.assertRaises(ValidationError):
            po.handle_order_response_advanced(False, 'XX')

    def test_edi_tracker_computation(self):
        """Test transaction creation."""
        po = self.po
        po._l10n_sg_peppol_send_order()
        self.assertEqual(len(po.l10n_sg_peppol_order_tx_ids), 1)

    def test_send_order_balance(self):
        """Test sending order balance requires partial delivery and creates a transaction."""
        po = self.po

        self.assertFalse(po.l10n_sg_peppol_can_send_order_balance)

        po.order_line[:1].qty_received = 3.0
        self.assertTrue(po.l10n_sg_peppol_can_send_order_balance)

        initial_tx_count = len(po.l10n_sg_peppol_order_tx_ids)
        po.action_send_order_balance()
        self.assertEqual(len(po.l10n_sg_peppol_order_tx_ids), initial_tx_count + 1)

        balance_tx = po.l10n_sg_peppol_order_tx_ids.filtered(
            lambda t: t.document_type == 'order_balance'
        )[:1]
        self.assertTrue(balance_tx)
        self.assertEqual(balance_tx.state, 'sent')

    def test_order_balance_xml_content(self):
        """Test XML reflects remaining quantity (ordered - received) and passes template validation."""
        po = self.po
        po.order_line[:1].qty_received = 3.0  # 10 ordered - 3 received = 7 remaining

        xml_bytes = self.env['purchase.edi.xml.ubl_bis3_order_balance'].build_order_balance_xml(po)

        ns = {
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
        }
        root = etree.fromstring(xml_bytes)

        self.assertEqual(root.find('cbc:OrderTypeCode', ns).text, '348')
        self.assertEqual(root.find('cac:OrderDocumentReference/cbc:ID', ns).text, po.name)

        line_qty = root.find('.//cac:OrderLine/cac:LineItem/cbc:Quantity', ns)
        self.assertAlmostEqual(float(line_qty.text), 7.0)

        line_ext = root.find('.//cac:OrderLine/cac:LineItem/cbc:LineExtensionAmount', ns)
        self.assertAlmostEqual(float(line_ext.text), 350.0)  # 7 * 50.0

        total = root.find('cac:AnticipatedMonetaryTotal/cbc:PayableAmount', ns)
        self.assertAlmostEqual(float(total.text), 350.0)

    @freeze_time('2024-01-05 03:00:00')
    def test_order_validity_period_export(self):
        """Test the order deadline is exported as the validity period only when it is still ahead,
        as a date in the company timezone, and not for an order change."""
        po = self.po
        self.env.company.partner_id.tz = 'Asia/Singapore'
        ns = {
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
        }

        def get_validity_end_date():
            root = etree.fromstring(self.env['purchase.edi.xml.ubl_bis3_order'].build_order_xml(po))
            return root.findtext('cac:ValidityPeriod/cbc:EndDate', namespaces=ns)

        # 23:00 UTC on the 10th is already the 11th in Singapore.
        po.date_order = datetime(2024, 1, 10, 23, 0, 0)
        self.assertEqual(get_validity_end_date(), '2024-01-11')

        # A deadline left to its default (the creation time) or already passed is not exported.
        po.button_reset_date_order()
        self.assertIsNone(get_validity_end_date())
        po.date_order = datetime(2024, 1, 4, 0, 0, 0)
        self.assertIsNone(get_validity_end_date())

        # An order change is for a confirmed order: it has no deadline to accept.
        po.date_order = datetime(2024, 1, 10, 23, 0, 0)
        po._l10n_sg_peppol_send_order()
        po.handle_order_response_advanced(False, 'AP')
        root = etree.fromstring(self.env['purchase.edi.xml.ubl_bis3_order_change'].build_order_change(po)['xml_content'])
        self.assertIsNone(root.find('cac:ValidityPeriod', ns))

    def test_delivery_export(self):
        """Test the delivery address is exported as a delivery location only with its country, as
        the location address requires one."""
        po = self.po
        ns = {
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
        }
        po.dest_address_id = self.env['res.partner'].create({
            'name': 'Site',
            'global_location_number': '5880000000010',
            'street': '4 New Road',
            'country_id': self.env.ref('base.sg').id,
        })

        def get_delivery():
            return etree.fromstring(self.env['purchase.edi.xml.ubl_bis3_order'].build_order_xml(po)).find('cac:Delivery', ns)

        delivery = get_delivery()
        self.assertEqual(delivery.findtext('cac:DeliveryLocation/cbc:ID', namespaces=ns), '5880000000010')
        self.assertEqual(delivery.findtext('cac:DeliveryLocation/cbc:Name', namespaces=ns), 'Site')
        self.assertEqual(delivery.findtext('cac:DeliveryLocation/cac:Address/cbc:StreetName', namespaces=ns), '4 New Road')

        po.dest_address_id.country_id = False
        self.assertIsNone(get_delivery())

        po.dest_address_id.phone = '+65 6000 0000'
        delivery = get_delivery()
        self.assertIsNone(delivery.find('cac:DeliveryLocation', ns))
        self.assertEqual(delivery.findtext('cac:DeliveryParty/cac:PartyName/cbc:Name', namespaces=ns), 'Site')

    # -------------------------------------------------------------------------
    # SEND WIZARD
    # -------------------------------------------------------------------------

    def _open_send_wizard(self, po):
        action = po.action_rfq_send()
        self.assertEqual(action['res_model'], 'purchase.order.send.wizard')
        return Form(self.env['purchase.order.send.wizard'].with_context(action['context']))

    def _get_vendor_emails(self, po):
        return po.message_ids.filtered(lambda m: m.message_type == 'comment' and self.partner_a in m.partner_ids)

    def _set_sending_methods(self, wizard_form, methods):
        wizard_form.sending_method_checkboxes = {
            key: {**vals, 'checked': key in methods}
            for key, vals in wizard_form.sending_method_checkboxes.items()
        }

    def test_send_wizard_peppol_only(self):
        po = self.po.with_context(send_rfq=True)
        wizard_form = self._open_send_wizard(po)
        self._set_sending_methods(wizard_form, {'peppol'})
        wizard_form.save().action_send()

        self.assertEqual(po.state, 'sent')
        self.assertEqual(po.l10n_sg_peppol_order_tx_ids.document_type, 'order')
        self.assertFalse(po.l10n_sg_peppol_can_send_order)
        self.assertFalse(self._get_vendor_emails(po))

    def test_send_wizard_email_and_peppol(self):
        po = self.po.with_context(send_rfq=True)
        wizard_form = self._open_send_wizard(po)
        self._set_sending_methods(wizard_form, {'email', 'peppol'})
        wizard = wizard_form.save()
        self.assertIn(self.partner_a, wizard.mail_partner_ids)
        self.assertTrue(wizard.subject)
        self.assertTrue(wizard.attachment_ids)

        wizard.action_send()

        self.assertEqual(po.state, 'sent')
        self.assertEqual(len(po.l10n_sg_peppol_order_tx_ids), 1)
        message = self._get_vendor_emails(po)
        self.assertEqual(len(message), 1)
        self.assertEqual(message.subject, wizard.subject)
        self.assertEqual(message.attachment_ids.res_model, 'purchase.order')
        self.assertEqual(message.attachment_ids.res_id, po.id)

    def test_send_wizard_previously_sent(self):
        self.po._l10n_sg_peppol_send_order()
        wizard_form = self._open_send_wizard(self.po)
        peppol_checkbox = wizard_form.sending_method_checkboxes['peppol']
        self.assertTrue(peppol_checkbox['readonly'])
        self.assertFalse(peppol_checkbox['checked'])
        self.assertIn('Previously sent', peppol_checkbox['label'])

    def test_send_wizard_vendor_without_peppol_id(self):
        self.partner_a.write({'routing_scheme': False, 'routing_endpoint': False})
        wizard_form = self._open_send_wizard(self.po)
        peppol_checkbox = wizard_form.sending_method_checkboxes['peppol']
        self.assertTrue(peppol_checkbox['readonly'])
        self.assertIn('Missing InvoiceNow (Peppol) ID', peppol_checkbox['label'])
        self.assertIn('l10n_sg_purchase_peppol_vendor_missing_peppol_id', wizard_form.alerts)

    def test_send_wizard_vendor_cannot_receive_orders(self):
        self.partner_a.with_company(self.env.company).peppol_supported_documents = []
        wizard_form = self._open_send_wizard(self.po)
        peppol_checkbox = wizard_form.sending_method_checkboxes['peppol']
        self.assertTrue(peppol_checkbox['readonly'])
        self.assertIn('Vendor cannot receive orders', peppol_checkbox['label'])
        self.assertIn('l10n_sg_purchase_peppol_vendor_cannot_receive_order', wizard_form.alerts)

    def test_send_wizard_peppol_error_rolls_back(self):
        wizard_form = self._open_send_wizard(self.po.with_context(send_rfq=True))
        self._set_sending_methods(wizard_form, {'peppol'})
        wizard = wizard_form.save()
        with (
            patch.object(PurchaseOrder, '_l10n_sg_peppol_send_document', side_effect=UserError("Access Point down")),
            self.assertRaisesRegex(UserError, "Access Point down"),
        ):
            wizard.action_send()

    def test_peppol_send_error_allows_resend(self):
        with patch.object(PurchaseOrder, '_l10n_sg_peppol_send_document', side_effect=UserError("Access Point down")):
            self.po._l10n_sg_peppol_send_order()
        self.assertEqual(self.po.l10n_sg_peppol_order_tx_ids.peppol_proxy_state, 'error')
        self.assertEqual(self.po.state, 'draft')
        self.assertTrue(self.po.l10n_sg_peppol_can_send_order)
