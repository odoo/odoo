from markupsafe import Markup

from odoo import models, _


class OrderEdiCommon(models.AbstractModel):
    _name = 'order.edi.common'
    _description = "Order EDI Common"

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

        return True

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

    # -------------------------------------------------------------------------
    # OVERRIDES
    # -------------------------------------------------------------------------

    def _get_order_type(self):
        """Return the order type"""
        pass

    def _get_order_qty_field(self):
        """Return the quantity field for the order type"""
        pass

    def _get_order_tax_field(self):
        """Return the tax field for the order type"""
        pass

    def _get_order_note_field(self):
        """Return the note field for the order type"""
        pass

    def _get_dest_address_field(self):
        """Return the destination address field for the order type"""
        pass

    def _get_order_type_code(self):
        """Return the order type code for the Order Transaction"""
        pass

    def _get_order_ref(self):
        """Returns the reference associated with the order partner"""
        pass

    def _get_order_partner_role(self):
        """Returns the role of the partner in the context of the order xml tree"""
        return "BuyerCustomer"
