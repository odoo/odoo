# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_default_invoice_address = fields.Boolean()
    is_default_delivery_address = fields.Boolean()

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

    def _can_edited_by_current_customer(self):
        """ Return whether customer can be edited by current user's customer. """
        self.ensure_one()
        commercial_partner = self.env.user.partner_id.commercial_partner_id
        if self == commercial_partner:
            return True
        children_partner_ids = self.env['res.partner']._search([
            ('id', 'child_of', commercial_partner.id),
            ('type', 'in', ('invoice', 'delivery', 'other')),
        ])
        return  self.id in children_partner_ids

    def _is_anonymous_customer(self):
        """ Hook to check if customer is anonymous. """
        return False
