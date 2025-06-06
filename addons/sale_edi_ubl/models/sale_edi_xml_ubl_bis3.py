from odoo import models, Command, _


class SaleEdiXmlUbl_Bis3(models.AbstractModel):
    _name = 'sale.edi.xml.ubl_bis3'
    _inherit = ['account.edi.xml.ubl_bis3']
    _description = "Sale BIS Ordering 3.5"

    # -------------------------------------------------------------------------
    # Order EDI Export
    # -------------------------------------------------------------------------

    def _get_line_allowance_charge_vals(self, currency, net_price, discount):
        allowance_charge_vals = super()._get_line_allowance_charge_vals(currency, net_price, discount)
        allowance_charge_vals['allowance_charge_reason'] = _('Discount')
        return allowance_charge_vals

    def _get_order_line_vals(self, order_lines, customer, supplier):
        filtered_order_lines = order_lines.filtered(lambda l: l.display_type not in ['line_note', 'line_section'])
        order_lines_to_process = []
        for line_id, line in enumerate(filtered_order_lines, 1):
            order_lines_to_process.append({
                'id': line_id,
                'quantity': line.product_uom_qty,
                'quantity_unit_code': self._get_uom_unece_code(line.product_uom_id),
                'line_extension_amount': line.price_subtotal,
                'currency': line.currency_id,
                'currency_dp': self._get_currency_decimal_places(line.currency_id),
                'allowance_charge_vals': self._get_line_allowance_charge_vals(line.currency_id, line.price_subtotal, line.discount),
                'price_vals': self._get_order_line_item_price_vals(line.price_unit, line.discount, line.currency_id, line.product_uom_id),
                'item': self._get_line_item_vals(line.product_id, line.name, customer, supplier, line.tax_ids),
            })
        return order_lines_to_process

    def _export_order_vals(self, sale_order):
        vals = super()._export_order_vals(sale_order)

        customer = sale_order.partner_id
        supplier = sale_order.company_id.partner_id
        customer_delivery_address = customer.child_ids.filtered(lambda child: child.type == 'delivery')
        delivery = (sale_order.partner_shipping_id
                    or (customer_delivery_address and customer_delivery_address[0])
                    or customer)
        order_line_vals = self._get_order_line_vals(sale_order.order_line, customer, supplier)

        vals['vals'].update({
            'order_type_code': 220,
            'validity_date': sale_order.validity_date,
            'originator_document_reference': sale_order.client_order_ref,
            'customer_party_vals': self._get_partner_party_vals(customer, role='customer'),
            'supplier_party_vals': self._get_partner_party_vals(supplier, role='supplier'),
            'delivery_party_vals': self._get_partner_party_vals(delivery, role='delivery'),
            'anticipated_monetary_total_vals': self._get_anticipated_monetary_total_vals(order_line_vals, sale_order.currency_id, sale_order.amount_total, sale_order.amount_paid),
            'order_lines': order_line_vals,
        })
        return vals

    # -------------------------------------------------------------------------
    # Order EDI Import
    # -------------------------------------------------------------------------

    def _retrieve_order_vals(self, order, tree):
        """ Fill order details by extracting details from xml tree.
        param order: Order to fill details from xml tree.
        param tree: Xml tree to extract details.
        :return: list of logs to add warning and information about data from xml.
        """
        order_vals, logs = super()._retrieve_order_vals(order, tree)
        order_vals.pop('note', False)   # The SO Terms & Conditions take precedence over the PO's
        partner, partner_logs = self._import_partner(
            order.company_id,
            **self._import_retrieve_partner_vals(tree, 'BuyerCustomer'),
        )
        if partner:
            order_vals['partner_id'] = partner.id
        order_vals['client_order_ref'] = tree.findtext('./{*}ID')
        order_vals['origin'] = tree.findtext('./{*}QuotationDocumentReference/{*}ID')

        delivery_partner, delivery_logs = self._import_partner(
            order.company_id,
            **self._import_retrieve_partner_vals(tree, 'Delivery'),
        )
        if delivery_partner:
            order_vals['partner_shipping_id'] = delivery_partner.id

        allowance_charges_line_vals, allowance_charges_logs = self._import_document_allowance_charges(tree, order, 'sale')
        lines_vals, line_logs = self._import_lines(order, tree, './{*}OrderLine/{*}LineItem', document_type='order', tax_type='sale')
        # adapt each line to sale.order.line
        for line in lines_vals:
            line['product_uom_qty'] = line.pop('quantity')
            # remove invoice line fields
            line.pop('deferred_start_date', False)
            line.pop('deferred_end_date', False)
            if not line.get('product_id'):
                line_logs.append(_("Could not retrieve the product named: %(name)s", name=line['name']))
        lines_vals += allowance_charges_line_vals

        # Update order with lines excluding discounts
        order_vals['order_line'] = [Command.create(line_vals) for line_vals in lines_vals]
        logs += partner_logs + delivery_logs + line_logs + allowance_charges_logs

        return order_vals, logs

    def _import_order_ubl(self, order, file_data, new):
        # Overriding the main method to recalculate the price unit and discount
        res = super()._import_order_ubl(order, file_data, new)
        # Recompute product price and discount according to sale price
        order._recompute_prices()
        return res
