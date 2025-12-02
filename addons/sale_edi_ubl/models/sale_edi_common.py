from markupsafe import Markup

from odoo import _, models


class SaleEdiCommon(models.AbstractModel):
    _name = 'sale.edi.common'
    _inherit = 'account.edi.common'
    _description = "Common functions for EDI orders"

    # -------------------------------------------------------------------------
    # Import order
    # -------------------------------------------------------------------------

    def _import_order_ubl(self, order, file_data):
        """ Common importing method to extract order data from file_data.

        :param order: Order to fill details from file_data.
        :param file_data: File data to extract order related data from.
        :return: True if there no exception while extraction.
        :rtype: Boolean
        """
        tree = file_data['xml_tree']

        # Update the order.
        logs = self._import_fill_order(order, tree)
        if order:
            body = Markup("<strong>%s</strong>") % \
                _("Format used to import the invoice: %s",
                  self.env['ir.model']._get(self._name).name)
            if logs:
                order._create_activity_set_details()
                body += Markup("<ul>%s</ul>") % \
                    Markup().join(Markup("<li>%s</li>") % l for l in logs)
            order.message_post(body=body)

        lines_with_products = order.order_line.filtered('product_id')
        # Recompute product price and discount according to sale price
        lines_with_products._compute_price_unit()
        lines_with_products._compute_discount()

        return True

    def _import_order_lines(self, order, tree, xpath):
        """ Import order lines from xml tree.

        :param order: Order to set order line on.
        :param tree: Xml tree to extract OrderLine from.
        :param xpath: Xpath for order line items.
        :return: Logging information related orderlines details.
        :rtype: List
        """
        logs = []
        lines_values = []
        for line_tree in tree.iterfind(xpath):
            line_values = self._retrieve_line_vals(line_tree)
            line_values = {
                **line_values,
                'product_uom_qty': line_values['quantity'],
                'product_uom': line_values['product_uom_id'],
            }
            del line_values['quantity']
            # To do: rename product_uom field to `product_uom_id` of sale.order.line
            del line_values['product_uom_id']
            if not line_values['product_id']:
                logs += [_("Could not retrieve product for line '%s'", line_values['name'])]
            # To do: rename tax_id field to `tax_ids` of sale.order.line
            line_values['tax_id'], tax_logs = self._retrieve_taxes(
                order, line_values, 'sale',
            )
            logs += tax_logs
            lines_values += self._retrieve_line_charges(order, line_values, line_values['tax_id'])
            if not line_values['product_uom']:
                line_values.pop('product_uom')  # if no uom, pop it so it's inferred from the product_id
            if line_values.get('discount'):  # Exclude discounts
                line_values.pop('discount')
            lines_values.append(line_values)

        return lines_values, logs

    def _import_payment_term_id(self, order, tree, xapth):
        """ Return payment term from given tree. """
        payment_term_note = self._find_value(xapth, tree)
        if not payment_term_note:
            return False

        return self.env['account.payment.term'].search([
            *self.env['account.payment.term']._check_company_domain(order.company_id),
            ('name', '=', payment_term_note)
        ], limit=1)

    def _import_delivery_partner(self, order, name, phone, email):
        """ Import delivery address from details if not found then log details."""
        logs = []
        dest_partner = self.env['res.partner'].with_company(
            order.company_id
        )._retrieve_partner(name=name, phone=phone, email=email)
        if not dest_partner:
            partner_detaits_str = self._get_partner_detail_str(name, phone, email)
            logs.append(_("Could not retrieve Delivery Address with Details: { %s }", partner_detaits_str))

        return dest_partner, logs

    def _import_partner(self, company_id, name, phone, email, vat, **kwargs):
        """ Override of edi.mixin to set current user partner if there is no matching partner
        found and log details related to partner."""
        partner, logs = super()._import_partner(company_id, name, phone, email, vat, **kwargs)
        if not partner:
            partner_detaits_str = self._get_partner_detail_str(name, phone, email, vat)
            if not vat:
                logs.append(_("Insufficient details to extract Customer: { %s }", partner_detaits_str))
            else:
                logs.append(_("Could not retrive Customer with Details: { %s }", partner_detaits_str))

        return partner, logs

    def _get_partner_detail_str(self, name, phone=False, email=False, vat=False):
        """ Return partner details string to help user find or create proper contact with details.
        """
        partner_details = _("Name: %(name)s, Vat: %(vat)s", name=name, vat=vat)
        if phone:
            partner_details += _(", Phone: %(phone)s", phone=phone)
        if email:
            partner_details += _(", Email: %(email)s", email=email)

        return partner_details
