from odoo import models, Command, _


class PurchaseEdiXmlUbl_Bis3(models.AbstractModel):
    _name = 'purchase.edi.xml.ubl_bis3'
    _inherit = ['account.edi.xml.ubl_bis3']
    _description = "Purchase UBL BIS Ordering 3.5"

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
                'quantity': line.product_qty,
                'quantity_unit_code': self._get_uom_unece_code(line.product_uom_id),
                'line_extension_amount': line.price_subtotal,
                'currency': line.currency_id,
                'currency_dp': self._get_currency_decimal_places(line.currency_id),
                'allowance_charge_vals': self._get_line_allowance_charge_vals(line.currency_id, line.price_subtotal, line.discount),
                'price_vals': self._get_order_line_item_price_vals(line.price_unit, line.discount, line.currency_id, line.product_uom_id),
                'item': self._get_line_item_vals(line.product_id, line.name, customer, supplier, line.tax_ids),
            })
        return order_lines_to_process

    def _export_order_vals(self, purchase_order):
        vals = super()._export_order_vals(purchase_order)

        customer = purchase_order.company_id.partner_id
        supplier = purchase_order.partner_id
        customer_delivery_address = customer.child_ids.filtered(lambda child: child.type == 'delivery')
        delivery = (purchase_order.dest_address_id
                    or (customer_delivery_address and customer_delivery_address[0])
                    or customer)
        order_line_vals = self._get_order_line_vals(purchase_order.order_line, customer, supplier)

        vals['vals'].update({
            'order_type_code': 105,
            'quotation_document_reference': purchase_order.partner_ref,
            'customer_party_vals': self._get_partner_party_vals(customer, role='customer'),
            'supplier_party_vals': self._get_partner_party_vals(supplier, role='supplier'),
            'delivery_party_vals': self._get_partner_party_vals(delivery, role='delivery'),
            'anticipated_monetary_total_vals': self._get_anticipated_monetary_total_vals(order_line_vals, purchase_order.currency_id, purchase_order.amount_total),
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
        partner, partner_logs = self._import_partner(
            order.company_id,
            **self._import_retrieve_partner_vals(tree, 'SellerSupplier'),
        )
        if partner:
            order_vals['partner_id'] = partner.id
        order_vals['partner_ref'] = tree.findtext('./{*}ID')
        order_vals['origin'] = tree.findtext('./{*}OriginatorDocumentReference/{*}ID')

        delivery_partner, delivery_logs = self._import_partner(
            order.company_id,
            **self._import_retrieve_partner_vals(tree, 'Delivery'),
        )
        if delivery_partner:
            order_vals['dest_address_id'] = delivery_partner.id

        allowance_charges_line_vals, allowance_charges_logs = self._import_document_allowance_charges(tree, order, 'purchase')
        lines_vals, line_logs = self._import_lines(order, tree, './{*}OrderLine/{*}LineItem', document_type='order', tax_type='purchase')
        # adapt each line to purchase.order.line
        for line in lines_vals:
            line['product_qty'] = line.pop('quantity')
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
