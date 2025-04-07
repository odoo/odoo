from lxml import etree

from odoo import _, models
from odoo.tools import html2plaintext, cleanup_xml_node


class OrderEdiXmlUbl_Bis3(models.AbstractModel):
    _name = 'order.edi.xml.ubl_bis3'
    _inherit = ['order.edi.common', 'account.edi.xml.ubl_bis3']
    _description = "UBL BIS 3 Peppol Order transaction 3.4"

    #####################################################################################
    ##### Order EDI Export
    #####################################################################################

    def _export_order_filename(self, order):
        return f"{order.name.replace('/', '_')}_ubl_bis3.xml"

    def _get_country_vals(self, country):
        return {
            'country': country,
            'identification_code': country.code,
            'name': country.name,
        }

    def _get_partner_address_vals(self, partner):
        vals = super()._get_partner_address_vals(partner)
        vals.pop('country_vals', None)
        vals['country_identification_code'] = partner.country_id.code
        return vals

    def _get_partner_party_tax_scheme_vals(self, partner):
        return {
            'company_id': partner.vat,
            'tax_scheme_vals': {'id': 'VAT'},
        }

    def _get_partner_party_legal_entity_vals(self, partner):
        return {
            'registration_name': partner.name,
            'company_id': partner.vat,
            'registration_address_vals': self._get_partner_address_vals(partner),
        }

    def _get_partner_party_vals(self, partner, role):
        vals = {
            'party_name': partner.display_name,
            'postal_address_vals': self._get_partner_address_vals(partner),
            'contact_vals': self._get_partner_contact_vals(partner),
        }
        if role == 'customer':
            vals['party_tax_scheme_vals'] = self._get_partner_party_tax_scheme_vals(partner.commercial_partner_id)
        return vals

    def _get_delivery_party_vals(self, delivery):
        return {
            'party_name': delivery.display_name,
            'postal_address_vals': self._get_partner_address_vals(delivery),
            'contact_vals': self._get_partner_contact_vals(delivery),
        }

    def _get_payment_terms_vals(self, payment_term):
        return {
            'note': payment_term.name
        }

    def _get_tax_category_vals(self, order, order_line):
        if not order_line.tax_ids:
            return None
        tax = order_line.tax_ids[0]
        customer = order.company_id.partner_id.commercial_partner_id
        supplier = order.partner_id
        tax_unece_codes = self._get_tax_unece_codes(customer, supplier, tax)
        return {
            'id': tax_unece_codes.get('tax_category_code'),
            'percent': tax.amount if tax.amount_type == 'percent' else False,
            'tax_scheme_vals': {'id': 'VAT'},
        }

    def _get_line_item_price_vals(self, line):
        """ Method used to fill the cac:Price node.
        It provides information about the price applied for the goods and services.
        """
        # Price subtotal without discount:
        net_price_subtotal = line.price_subtotal
        # Price subtotal with discount:
        if line.discount == 100.0:
            gross_price_subtotal = 0.0
        else:
            gross_price_subtotal = line.currency_id.round(net_price_subtotal / (1.0 - (line.discount or 0.0) / 100.0))
        # Price subtotal with discount / quantity:
        line_qty = line[self._get_order_qty_field()]
        gross_price_unit = gross_price_subtotal / line_qty if line_qty else 0.0

        uom = self._get_uom_unece_code(line.product_uom_id)

        vals = {
            'currency_id': line.currency_id.name,
            'currency_dp': self._get_currency_decimal_places(line.currency_id),
            'price_amount': round(gross_price_unit, 10),
            'product_price_dp': self.env['decimal.precision'].precision_get('Product Price'),
            'base_quantity': 1,
            'base_quantity_unit_code': uom,
        }

        return vals

    def _get_anticipated_monetary_total_vals(self, order, order_lines):
        line_extension_amount = sum(line['line_extension_amount'] for line in order_lines)
        allowance_total_amount = sum(line['price']['allowance_charge_vals']['amount'] for line in order_lines if 'allowance_charge_vals' in line['price'])
        return {
            'currency': order.currency_id,
            'currency_dp': self._get_currency_decimal_places(order.currency_id),
            'line_extension_amount': line_extension_amount,
            'allowance_total_amount': allowance_total_amount,
            'tax_exclusive_amount': line_extension_amount - allowance_total_amount,
            'tax_inclusive_amount': order.amount_total,
            'payable_amount': order.amount_total,
        }

    def _get_item_vals(self, order, order_line):
        product = order_line.product_id
        variant_info = [{
            'name': value.attribute_id.name,
            'value': value.name
        } for value in product.product_template_attribute_value_ids]

        vals = {
            'name': product.name or order_line.name,
            'description': order_line.name or product.description,
            'standard_item_identification': product.barcode,
            'classified_tax_category_vals': self._get_tax_category_vals(order, order_line)
        }

        if len(variant_info) > 0:
            vals['variant_info'] = variant_info
        return vals

    def _get_order_lines(self, order):
        qty_field = self._get_order_qty_field()
        filtered_order_lines = order.order_line.filtered(lambda l: l.display_type not in ['line_note', 'line_section'])
        order_lines_to_process = []
        for line_id, line in enumerate(filtered_order_lines, 1):
            order_lines_to_process.append({
                'id': line_id,
                'quantity': line[qty_field],
                'quantity_unit_code': self._get_uom_unece_code(line.product_uom_id),
                'line_extension_amount': line.price_subtotal,
                'currency_id': line.currency_id.name,
                'currency_dp': self._get_currency_decimal_places(line.currency_id),
                'price': self._get_line_item_price_vals(line),
                'item': self._get_item_vals(order, line),
            })
        return order_lines_to_process

    def _export_order_vals(self, order):
        order_lines = self._get_order_lines(order)
        anticipated_monetary_total_vals = self._get_anticipated_monetary_total_vals(order, order_lines)

        supplier = order._get_supplier_id()
        customer = order.company_id.partner_id.commercial_partner_id
        customer_delivery_address = customer.child_ids.filtered(lambda child: child.type == 'delivery')
        delivery = (
            order[self._get_dest_address_field()]
            or (customer_delivery_address and customer_delivery_address[0])
            or customer
        )

        vals = {
            'builder': self,
            'order': order,
            'supplier': supplier,
            'customer': customer,

            'format_float': self.format_float,

            'vals': {
                'id': order.name,
                'issue_date': order.create_date.date(),
                'order_type_code': self._get_order_type_code(),
                'note': html2plaintext(order.note) if order.note else False,
                'originator_document_reference': order.origin,
                'document_currency_code': order.currency_id.name.upper(),
                'delivery_party_vals': self._get_delivery_party_vals(delivery),
                'supplier_party_vals': self._get_partner_party_vals(supplier, role='supplier'),
                'customer_party_vals': self._get_partner_party_vals(customer, role='customer'),
                'payment_terms_vals': self._get_payment_terms_vals(order.payment_term_id),
                'anticipated_monetary_total_vals': anticipated_monetary_total_vals,
                'tax_amount': order.amount_tax,
                'order_lines': order_lines,
                'currency_dp': self._get_currency_decimal_places(order.currency_id),  # currency decimal places
                'currency_id': order.currency_id.name,
            },
        }

        return vals

    def _export_order(self, order):
        vals = self._export_order_vals(order)
        xml_content = self.env['ir.qweb']._render('order_edi_ubl_cii.bis3_OrderType', vals)
        return etree.tostring(cleanup_xml_node(xml_content), xml_declaration=True, encoding='UTF-8')
