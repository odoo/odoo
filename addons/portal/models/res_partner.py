# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Domain


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_frontend_writable_fields(self):
        """Define the fields a portal/public user can change on their contact and address records.

        :rtype: set
        """
        return {
            'name', 'phone', 'email', 'street', 'street2', 'city', 'state_id', 'country_id', 'zip',
            'zipcode', 'vat', 'company_name',
        }

    def _can_edit_country(self):
        self.ensure_one()
        return True

    def can_edit_vat(self):
        """ `vat` is a commercial field, synced between the parent (commercial
        entity) and the children. Only the commercial entity should be able to
        edit it (as in backend)."""
        self.ensure_one()
        return not self.parent_id

    def _can_be_edited_by_current_customer(self, **kwargs):
        """Return whether partner can be edited by current user."""
        self.ensure_one()
        if self == self._get_current_partner(**kwargs):
            return True
        children_partner_ids = self.env['res.partner']._search([
            ('id', 'child_of', self.commercial_partner_id.id),
            ('type', 'in', ('invoice', 'delivery', 'other')),
        ])
        return self.id in children_partner_ids

    @api.model
    def _get_current_partner(self, **kwargs):
        """ Get main partner of the current user base on logged in user and kwargs. """
        if self.env.user._is_public():
            return self.env['res.partner']
        return self.env.user.partner_id

    def _get_delivery_address_domain(self):
        return Domain([
            ('id', 'child_of', self.ids),
            '|', ('type', 'in', ['delivery', 'other']), ('id', '=', self.id),
        ])
