# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_default_billing_address = fields.Boolean(default=False, store=True)
    is_default_shipping_address = fields.Boolean(default=False, store=True)

    def _update_delivery_and_shipping_address(self, partner_id, address_type, **kw):
        partner_sudo = self.browse(partner_id)

        address_type = 'invoice' if address_type == 'invoice' or address_type == 'billing' else 'delivery'
        default_field = 'is_default_billing_address' if address_type == 'invoice' else 'is_default_shipping_address'
        if partner_sudo.parent_id:
            partner_sudo.parent_id.child_ids.filtered(lambda p: p.type == address_type or p.type == 'other').write({default_field: False})
            partner_sudo.parent_id.child_ids.filtered(lambda p: p.type == address_type).write({'type': 'other'})
            partner_sudo.parent_id.write({default_field: False})
        else:
            partner_sudo.child_ids.filtered(lambda p: p.type == address_type or p.type == 'other').write({default_field: False})
            partner_sudo.child_ids.filtered(lambda p: p.type == address_type).write({'type': 'other'})
        if partner_sudo.type == 'contact':
            partner_sudo.write({default_field: True})
        else:
            partner_sudo.write({default_field: True, 'type': address_type})

        return partner_sudo.address_get([address_type])

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

    def can_edit_info(self):
        """ Overide this method to allow user to change address information. """
        return True

    def _can_be_edited_by_current_customer(self, address_type, **kwargs):
        self.ensure_one()
        commercial_partner_id = self.env.user.partner_id.commercial_partner_id.id
        children_partner_ids = self.env['res.partner']._search([
            ('id', 'child_of', commercial_partner_id),
            ('type', 'in', ('invoice', 'delivery', 'other')),
        ])
        return self.id in children_partner_ids or self.id == commercial_partner_id
