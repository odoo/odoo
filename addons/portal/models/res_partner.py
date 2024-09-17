# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_default_billing_address = fields.Boolean()
    is_default_shipping_address = fields.Boolean()

    def _can_edit_name(self):
        """ Name can be changed more often than the VAT """
        self.ensure_one()
        return True

    def can_edit_vat(self):
        """ `vat` is a commercial field, synced between the parent (commercial
        entity) and the children. Only the commercial entity should be able to
        edit it (as in backend)."""
        self.ensure_one()
        return not self.parent_id

    def _can_edit_info(self):
        """ Overide this method to allow user to change address information. """
        self.ensure_one()
        return True

    def _can_be_edited_by_current_partner(self, **kwargs):
        self.ensure_one()
        commercial_partner_id = kwargs.get('parent_id', self.env.user.partner_id.commercial_partner_id.id)
        children_partner_ids = self.env['res.partner']._search([
            ('id', 'child_of', commercial_partner_id),
            ('type', 'in', ('invoice', 'delivery', 'other')),
        ])
        return self.id in children_partner_ids or self.id == commercial_partner_id

    def _update_default_address(self, address_type):
        """ Update the current address as the default one in his address type. """
        self.ensure_one()
        address_type = 'invoice' if address_type == 'invoice' or address_type == 'billing' else 'delivery'
        default_field = 'is_default_billing_address' if address_type == 'invoice' else 'is_default_shipping_address'
        if self.parent_id:
            all_partners = self.parent_id.child_ids.filtered(lambda p: p.type == address_type or p.type == 'other') + self.parent_id
        else:
            all_partners = self.child_ids.filtered(lambda p: p.type == address_type or p.type == 'other')
        # The default address type is set to 'other' to ease reusability and don't confuse customer
        all_partners.filtered(lambda p: p.type == address_type).write({'type': 'other'})
        all_partners.write({default_field: False})

        self.write({default_field: True})
        if self.type != 'contact':
            self.write({'type': address_type})

        return self.address_get([address_type])
