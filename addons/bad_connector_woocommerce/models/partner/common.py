import hashlib
import logging

from odoo import _, fields, models

from odoo.addons.component.core import Component
from odoo.addons.connector.exception import MappingError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    woo_bind_ids = fields.One2many(
        comodel_name="woo.res.partner",
        inverse_name="odoo_id",
        string="WooCommerce Bindings",
        copy=False,
    )
    firstname = fields.Char(string="First Name")
    lastname = fields.Char(string="Last Name")
    hash_key = fields.Char(string="Hash Key")

    def write(self, vals):
        """
        Update specific fields in the partner record and set 'hash_key' to False if
        certain fields are modified.
        """
        if set(vals.keys()) & {
            "firstname",
            "lastname",
            "email",
            "mobile",
            "phone",
            "street",
            "street2",
            "city",
            "state_id",
            "zip",
            "country_id",
        }:
            vals["hash_key"] = False

        return super(ResPartner, self).write(vals)

    def _prepare_child_partner_vals(self, data, address_type=None):
        """Prepare values for child_ids"""
        country = data.get("country")
        state = data.get("state")
        country_record = self.env["res.country"].search(
            [("code", "=", country)],
            limit=1,
        )
        if country and not country_record:
            raise MappingError(_(f"Country '{country}' not found in Odoo records."))
        state_record = self.env["res.country.state"].search(
            [("code", "=", state), ("country_id", "=", country_record.id)], limit=1
        )
        if state and not state_record:
            raise MappingError(
                _(
                    f"State code '{state}' not found in Odoo records for "
                    "country '{country}'."
                )
            )
        vals = {
            "name": data.get("username", "")
            or data.get("first_name", "")
            and data.get("last_name", "")
            and f"{data.get('first_name')} {data.get('last_name')}"
            or data.get("first_name", "")
            or data.get("email", ""),
            "firstname": data.get("first_name", ""),
            "lastname": data.get("last_name", ""),
            "email": data.get("email", ""),
            "type": address_type or "",
            "street": data.get("address_1"),
            "street2": data.get("address_2"),
            "zip": data.get("postcode"),
            "phone": data.get("phone"),
            "country_id": country_record.id if country_record else False,
            "state_id": state_record.id if state_record else False,
            "city": data.get("city"),
        }
        return vals

    def _process_address_data(self, data, address_type, partner_ext_id, backend_id):
        """
        Process address data, generate hash key, and handle partner creation or
        retrieval.
        """
        hash_attributes = (
            data.get("username"),
            data.get("first_name"),
            data.get("last_name"),
            data.get("email"),
            data.get("address_1"),
            data.get("address_2"),
            data.get("city"),
            data.get("country"),
            data.get("state"),
            address_type,
            data.get("postcode"),
            data.get("phone"),
            partner_ext_id,
            backend_id,
        )
        hash_key = hashlib.md5(
            "|".join(str(attr) for attr in hash_attributes).encode()
        ).hexdigest()
        existing_partner = self.env["res.partner"].search(
            [("hash_key", "=", hash_key)], limit=1
        )
        if existing_partner:
            return
        address_data = self._prepare_child_partner_vals(data, address_type)
        address_data["hash_key"] = hash_key
        return address_data

    def create_get_children(self, record, partner_ext_id, backend_id):
        """Return the Invoice and Shipping Addresses"""
        billing = record.get("billing")
        shipping = record.get("shipping")
        child_data = []
        for data, address_type in [(billing, "invoice"), (shipping, "delivery")]:
            if not any(data.values()):
                continue
            if (
                not data.get("email")
                and not backend_id.without_email
                and address_type != "delivery"
            ):
                raise MappingError(_("Email is Missing!"))
            address_data = self._process_address_data(
                data, address_type, partner_ext_id, backend_id
            )
            if not address_data:
                continue
            child_data.append(address_data)
        return child_data


class WooResPartner(models.Model):
    _name = "woo.res.partner"
    _inherit = "woo.binding"
    _inherits = {"res.partner": "odoo_id"}
    _description = "WooCommerce Partner"

    _rec_name = "name"

    odoo_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        required=True,
        ondelete="restrict",
    )


class WooResPartnerAdapter(Component):
    """Adapter for WooCommerce Res Partner"""

    _name = "woo.res.partner.adapter"
    _inherit = "woo.adapter"
    _apply_on = "woo.res.partner"
    _woo_model = "customers"
    _odoo_ext_id_key = "id"
    _check_import_sync_date = True
