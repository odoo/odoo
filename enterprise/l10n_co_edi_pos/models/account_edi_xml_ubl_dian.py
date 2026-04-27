from odoo import models

from lxml import etree


class AccountEdiXmlUBLDian(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_dian'

    def _export_invoice(self, invoice):
        # Force the use of the new helpers on invoices created from PoS orders in order to handle tips.
        if invoice.pos_order_ids:
            xml, errors = self._export_invoice_new(invoice)
            root = etree.fromstring(xml)
            cert_sudo = invoice.company_id.sudo().l10n_co_dian_certificate_ids[-1]
            self._dian_fill_signed_info_and_signature(root, cert_sudo)
            return etree.tostring(root, encoding='UTF-8'), errors
        return super()._export_invoice(invoice)

    def _is_document_allowance_charge(self, base_line):
        return super()._is_document_allowance_charge(base_line) or base_line.get('is_tip')

    def _add_invoice_base_lines_vals(self, vals):
        super()._add_invoice_base_lines_vals(vals)
        invoice = vals['invoice']

        if (pos_order := invoice.pos_order_ids) and pos_order.is_tipped:
            tip_product = pos_order.config_id.tip_product_id
            for base_line in vals['base_lines']:
                if base_line['product_id'] == tip_product:
                    base_line['is_tip'] = True

    def _get_document_allowance_charge_node(self, vals):
        base_line = vals['base_line']
        if not base_line.get('is_tip'):
            allowance_charge_node = super()._get_document_allowance_charge_node(vals)
            return {
                'cbc:ID': {'_text': '1' if allowance_charge_node['cbc:ChargeIndicator'] == 'true' else '2'},
                **allowance_charge_node,
            }

        base_amount = vals['tax_inclusive_amount'] - base_line['tax_details']['total_excluded']

        return {
            'cbc:ID': {'_text': '1'},
            'cbc:ChargeIndicator': {'_text': 'true'},
            'cbc:AllowanceChargeReasonCode': {'_text': '03'},
            'cbc:AllowanceChargeReason': {'_text': 'Propina'},
            'cbc:Amount': {
                '_text': self.format_float(base_line['tax_details']['total_excluded'], vals['currency_dp']),
                'currencyID': vals['currency_name']
            },
            'cbc:BaseAmount': {
                '_text': self.format_float(base_amount, vals['currency_dp']),
                'currencyID': vals['currency_name']
            },
            'cbc:MultiplierFactorNumeric': {'_text': (base_line['tax_details']['total_excluded'] / base_amount) * 100},
        }
