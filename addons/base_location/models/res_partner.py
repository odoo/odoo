# Copyright 2016 Nicolas Bessi, Camptocamp SA
# Copyright 2018 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    zip_id = fields.Many2one(
        comodel_name="res.city.zip",
        string="ZIP Location",
        index=True,
        compute="_compute_zip_id",
        readonly=False,
        store=True,
    )
    city_id = fields.Many2one(
        index=True,  # add index for performance
        compute="_compute_city_id",
        readonly=False,
        store=True,
    )
    city = fields.Char(compute="_compute_city", readonly=False, store=True)
    zip = fields.Char(compute="_compute_zip", readonly=False, store=True)
    country_id = fields.Many2one(
        compute="_compute_country_id", readonly=False, store=True
    )
    state_id = fields.Many2one(compute="_compute_state_id", readonly=False, store=True)

    @api.depends("state_id", "country_id", "city_id", "zip")
    def _compute_zip_id(self):
        """Empty the zip auto-completion field if data mismatch when on UI."""
        for record in self.filtered("zip_id"):
            fields_map = {
                "zip": "name",
                "city_id": "city_id",
                "state_id": "state_id",
                "country_id": "country_id",
            }
            for rec_field, zip_field in fields_map.items():
                if (
                    record[rec_field]
                    and record[rec_field] != record._origin[rec_field]
                    and record[rec_field] != record.zip_id[zip_field]
                ):
                    record.zip_id = False
                    break

    @api.depends("zip_id")
    def _compute_city_id(self):
        if hasattr(super(), "_compute_city_id"):
            return super()._compute_city_id()  # pragma: no cover
        for record in self:
            if record.zip_id:
                record.city_id = record.zip_id.city_id
            elif not record.country_enforce_cities:
                record.city_id = False

    @api.depends("zip_id")
    def _compute_city(self):
        if hasattr(super(), "_compute_city"):
            return super()._compute_city()  # pragma: no cover
        for record in self:
            if record.zip_id:
                record.city = record.zip_id.city_id.name

    @api.depends("zip_id")
    def _compute_zip(self):
        if hasattr(super(), "_compute_zip"):
            return super()._compute_zip()  # pragma: no cover
        for record in self:
            if record.zip_id:
                record.zip = record.zip_id.name

    @api.depends("zip_id", "state_id")
    def _compute_country_id(self):
        if hasattr(super(), "_compute_country_id"):
            return super()._compute_country_id()  # pragma: no cover
        for record in self:
            if record.zip_id.city_id.country_id:
                record.country_id = record.zip_id.city_id.country_id
            elif record.state_id:
                record.country_id = record.state_id.country_id

    @api.depends("zip_id")
    def _compute_state_id(self):
        if hasattr(super(), "_compute_state_id"):
            return super()._compute_state_id()  # pragma: no cover
        for record in self:
            state = record.zip_id.city_id.state_id
            if state and record.state_id != state:
                record.state_id = record.zip_id.city_id.state_id

    @api.constrains("zip_id", "country_id", "city_id", "state_id", "zip")
    def _check_zip(self):
        if self.env.context.get("skip_check_zip"):
            return
        for rec in self:
            if not rec.zip_id:
                continue
            error_dict = {"partner": rec.name, "location": rec.zip_id.name}
            if rec.zip_id.city_id.country_id != rec.country_id:
                raise ValidationError(
                    _(
                        "The country of the partner %(partner)s differs from that in "
                        "location %(location)s"
                    )
                    % error_dict
                )
            if rec.zip_id.city_id.state_id != rec.state_id:
                raise ValidationError(
                    _(
                        "The state of the partner %(partner)s differs from that in "
                        "location %(location)s"
                    )
                    % error_dict
                )
            if rec.zip_id.city_id != rec.city_id:
                raise ValidationError(
                    _(
                        "The city of the partner %(partner)s differs from that in "
                        "location %(location)s"
                    )
                    % error_dict
                )
            if rec.zip_id.name != rec.zip:
                raise ValidationError(
                    _(
                        "The zip of the partner %(partner)s differs from that in "
                        "location %(location)s"
                    )
                    % error_dict
                )

    def _zip_id_domain(self):
        return """
            [
                ("city_id", "=?", city_id),
                ("city_id.country_id", "=?", country_id),
                ("city_id.state_id", "=?", state_id),
            ]
        """

    @api.model
    def _fields_view_get_address(self, arch):
        # We want to use a domain that requires city_id to be on the view
        # but we can't add it directly there, otherwise _fields_view_get_address
        # in base_address_extended won't do its magic, as it immediately returns
        # if city_id is already in there. On the other hand, if city_id is not in the
        # views, odoo won't let us use it in zip_id's domain.
        # For this reason we need to set the domain here.
        arch = super()._fields_view_get_address(arch)
        doc = etree.fromstring(arch)
        for node in doc.xpath("//field[@name='zip_id']"):
            node.attrib["domain"] = self._zip_id_domain()
        return etree.tostring(doc, encoding="unicode")

    @api.model
    def _address_fields(self):
        """Add to the list of address fields the new ZIP one, but also the city that is
        not added by `base_address_extended`.
        """
        return super()._address_fields() + ["zip_id", "city_id"]
