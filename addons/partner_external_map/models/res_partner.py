# Copyright 2015 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# Copyright 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# Copyright 2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, models
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _address_as_string(self):
        self.ensure_one()
        addr = []
        if self.street:
            addr.append(self.street)
        if self.street2:
            addr.append(self.street2)
        if hasattr(self, "street3") and self.street3:
            addr.append(self.street3)
        if self.city:
            addr.append(self.city)
        if self.state_id:
            addr.append(self.state_id.name)
        if self.country_id:
            addr.append(self.country_id.name)
        if not addr:
            raise UserError(_("Address missing on partner '%s'.") % self.name)
        return " ".join(addr)

    @api.model
    def _prepare_url(self, url, replace):
        assert url, "Missing URL"
        for key, value in replace.items():
            if not isinstance(value, str):
                # for latitude and longitude which are floats
                if isinstance(value, float):
                    value = "%.5f" % value
                else:
                    value = ""
            url = url.replace(key, value)
        logger.debug("Final URL: %s", url)
        return url

    def open_map(self):
        self.ensure_one()
        map_website = self.env.user.context_map_website_id
        if not map_website:
            raise UserError(
                _("Missing map provider: " "you should set it in your preferences.")
            )
        # Since v13, fields partner_latitude and partner_longitude are
        # in the "base" module
        if map_website.lat_lon_url and self.partner_latitude and self.partner_longitude:
            url = self._prepare_url(
                map_website.lat_lon_url,
                {
                    "{LATITUDE}": self.partner_latitude,
                    "{LONGITUDE}": self.partner_longitude,
                },
            )
        else:
            if not map_website.address_url:
                raise UserError(
                    _(
                        "Missing parameter 'URL that uses the address' "
                        "for map website '%s'."
                    )
                    % map_website.name
                )
            url = self._prepare_url(
                map_website.address_url, {"{ADDRESS}": self._address_as_string()}
            )
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def open_route_map(self):
        self.ensure_one()
        if not self.env.user.context_route_map_website_id:
            raise UserError(
                _(
                    "Missing route map website: "
                    "you should set it in your preferences."
                )
            )
        map_website = self.env.user.context_route_map_website_id
        if not self.env.user.context_route_start_partner_id:
            raise UserError(
                _(
                    "Missing start address for route map: "
                    "you should set it in your preferences."
                )
            )
        start_partner = self.env.user.context_route_start_partner_id
        if (
            map_website.route_lat_lon_url
            and self.partner_latitude
            and self.partner_longitude
            and start_partner.partner_latitude
            and start_partner.partner_longitude
        ):
            url = self._prepare_url(  # pragma: no cover
                map_website.route_lat_lon_url,
                {
                    "{START_LATITUDE}": start_partner.partner_latitude,
                    "{START_LONGITUDE}": start_partner.partner_longitude,
                    "{DEST_LATITUDE}": self.partner_latitude,
                    "{DEST_LONGITUDE}": self.partner_longitude,
                },
            )
        else:
            if not map_website.route_address_url:
                raise UserError(
                    _(
                        "Missing route URL that uses the addresses "
                        "for the map website '%s'"
                    )
                    % map_website.name
                )
            url = self._prepare_url(
                map_website.route_address_url,
                {
                    "{START_ADDRESS}": start_partner._address_as_string(),
                    "{DEST_ADDRESS}": self._address_as_string(),
                },
            )
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }
