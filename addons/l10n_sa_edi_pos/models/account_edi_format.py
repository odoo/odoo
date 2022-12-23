from odoo import models, _
from odoo.exceptions import UserError
from odoo.addons.l10n_sa_edi.models.account_edi_format import ZATCA_API_URLS
from base64 import b64decode
from lxml import etree


class EDIFormat(models.Model):
    _inherit = 'account.edi.format'

    def _l10n_sa_prepare_values(self, invoice):
        """
            Override to take into account Simplified invoice values
        """
        values = super()._l10n_sa_prepare_values(invoice)
        # Get the payment means from the pos's payment method, else use 'unknown' until a payment is registered
        # for the invoice.
        payment_means = 'unknown'
        if invoice.pos_order_ids:
            payment_means = invoice.pos_order_ids.payment_ids.payment_method_id.type
        is_export_invoice = invoice.partner_id.country_id != invoice.company_id.country_id and not invoice.pos_order_ids
        values.update({
            'payment_means_code': {
                'bank': 42,
                'card': 48,
                'cash': 10,
                'transfer': 30,
                'unknown': 1
            }[payment_means],
            'invoice_transaction_code': '0%s00%s00' % (
                '2' if invoice.pos_order_ids else '1',
                '1' if is_export_invoice else '0'
            ),
            'is_export_invoice': is_export_invoice,
        })
        return values

    def _l10n_sa_assert_clearance_status(self, invoice, clearance_data):
        """
            Override to add a check for the Reporting API
        """
        mode = 'reporting' if invoice.pos_order_ids else 'clearance'
        if mode == 'clearance' and clearance_data.get('clearanceStatus', '') != 'CLEARED':
            raise UserError(_("Invoice could not be cleared: \r\n %s ") % clearance_data)
        elif mode == 'reporting' and clearance_data.get('reportingStatus', '') != 'REPORTED':
            raise UserError(_("Invoice could not be reported: \r\n %s ") % clearance_data)

    def _l10n_sa_get_api_clearance(self, invoice):
        """
            Override to use the reporting api instead of clearance in the case of simplified invoices
        """
        return ZATCA_API_URLS['apis']['reporting' if invoice.pos_order_ids else 'clearance']

    def _l10n_sa_post_einvoice_submission(self, invoice, signed_xml, clearance_data):
        """
            Override to return the signed XML content as is in case of a simplified Invoice
        """
        if invoice.pos_order_ids:
            # if invoice originates from POS, it is a SIMPLIFIED invoice, and thus it is only reported and returns
            # no signed invoice. In this case, we just return the original content
            return signed_xml.decode()
        return b64decode(clearance_data['clearedInvoice']).decode()

    def _l10n_sa_apply_qr_code(self, invoice, xml_content):
        """
            Apply QR code on Invoice UBL content
        :return: XML content with QR code applied
        """
        root = etree.fromstring(xml_content)
        qr_code = invoice.with_context(from_pos=True).l10n_sa_qr_code_str
        qr_node = root.xpath('//*[local-name()="ID"][text()="QR"]/following-sibling::*/*')[0]
        qr_node.text = qr_code
        return etree.tostring(root, with_tail=False)

    def _l10n_sa_get_signed_xml(self, invoice, unsigned_xml, x509_cert):
        """
            Override to apply QR code once the invoice is signed and originates from the POS
        """
        signed_xml = super()._l10n_sa_get_signed_xml(invoice, unsigned_xml, x509_cert)
        if invoice.pos_order_ids:
            return self._l10n_sa_apply_qr_code(invoice, signed_xml)
        return signed_xml

