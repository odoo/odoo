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
            'zipcode', 'vat', 'parent_name',
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
        current_partner = self._get_current_partner(**kwargs)
        if self == current_partner:
            return True
        children_partner_ids = self.env['res.partner']._search([
            ('id', 'child_of', current_partner.commercial_partner_id.id),
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

    def _check_billing_address(self, **kwargs):
        """Check that all mandatory billing fields are filled for the given partner.

        :return: Whether all mandatory fields are filled.
        :rtype: bool
        """
        self.ensure_one()
        mandatory_billing_fields = self._get_mandatory_billing_address_fields(
            self.country_id, **kwargs
        )
        return all(self.read(mandatory_billing_fields)[0].values())

    def _get_mandatory_billing_address_fields(self, country_sudo, **kwargs):
        """Return the set of mandatory billing field names.

        :return: The set of mandatory billing field names.
        :rtype: set
        """
        base_fields = {'name', 'email'}
        if not self._needs_address(**kwargs):
            return base_fields
        base_fields.add('phone')  # not required for quick checkout (event)
        return base_fields | self._get_mandatory_address_fields(country_sudo, **kwargs)

    def _check_delivery_address(self, **kwargs):
        """Check that all mandatory delivery fields are filled for the given partner.

        :param res.partner partner_sudo: The partner whose delivery address to check.
        :return: Whether all mandatory fields are filled.
        :rtype: bool
        """
        self.ensure_one()
        mandatory_delivery_fields = self._get_mandatory_delivery_address_fields(
            self.country_id, **kwargs
        )
        return all(self.read(mandatory_delivery_fields)[0].values())

    def _get_mandatory_delivery_address_fields(self, country_sudo, **kwargs):
        """Return the set of mandatory delivery field names.

        :return: The set of mandatory delivery field names.
        :rtype: set
        """
        base_fields = {'name', 'email'}
        if not self._needs_address(**kwargs):
            return base_fields
        base_fields.add('phone')  # not required for quick checkout (event)
        return base_fields | self._get_mandatory_address_fields(country_sudo, **kwargs)

    def _needs_address(self, **_kwargs):
        """Hook meant to be overridden in other modules."""
        return True

    def _get_mandatory_address_fields(self, country_sudo, **_kwargs):
        """Return the set of common mandatory address fields.

        :param res.country country_sudo: The country to use to build the set of mandatory fields.
        :return: The set of common mandatory address field names.
        :rtype: set
        """
        field_names = {'street', 'city', 'country_id'}
        if country_sudo.state_required:
            field_names.add('state_id')
        if country_sudo.zip_required:
            field_names.add('zip')
        return field_names
