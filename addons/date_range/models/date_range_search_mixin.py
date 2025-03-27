# Copyright 2021 Opener B.V. <stefan@opener.amsterdam>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from lxml import etree

from odoo import _, api, fields, models
from odoo.osv.expression import FALSE_DOMAIN, NEGATIVE_TERM_OPERATORS, TRUE_DOMAIN


class DateRangeSearchMixin(models.AbstractModel):
    _name = "date.range.search.mixin"
    _description = "Mixin class to add a Many2one style period search field"
    _date_range_search_field = "date"

    date_range_search_id = fields.Many2one(
        comodel_name="date.range",
        string="Filter by period (technical field)",
        compute="_compute_date_range_search_id",
        search="_search_date_range_search_id",
    )

    def _compute_date_range_search_id(self):
        """Assign a dummy value for this search field"""
        for record in self:
            record.date_range_search_id = False

    @api.model
    def _search_date_range_search_id(self, operator, value):
        """Map the selected date ranges to the model's date field"""
        # Deal with some bogus values
        if not value:
            if operator in NEGATIVE_TERM_OPERATORS:
                return TRUE_DOMAIN
            return FALSE_DOMAIN
        if value is True:
            if operator in NEGATIVE_TERM_OPERATORS:
                return FALSE_DOMAIN
            return TRUE_DOMAIN
        # Assume from here on that the value is a string,
        # a single id or a list of ids
        ranges = self.env["date.range"]
        if isinstance(value, str):
            ranges = self.env["date.range"].search([("name", operator, value)])
        else:
            if isinstance(value, int):
                value = [value]
            sub_op = "not in" if operator in NEGATIVE_TERM_OPERATORS else "in"
            ranges = self.env["date.range"].search([("id", sub_op, value)])
        if not ranges:
            return FALSE_DOMAIN
        domain = (len(ranges) - 1) * ["|"] + sum(
            (
                [
                    "&",
                    (self._date_range_search_field, ">=", date_range.date_start),
                    (self._date_range_search_field, "<=", date_range.date_end),
                ]
                for date_range in ranges
            ),
            [],
        )
        return domain

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        """Inject the dummy Many2one field in the search view"""
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type != "search":
            return result
        root = etree.fromstring(result["arch"])
        if root.xpath("//field[@name='date_range_search_id']"):
            # Field was inserted explicitely
            return result
        separator = etree.Element("separator")
        field = etree.Element(
            "field",
            attrib={
                "name": "date_range_search_id",
                "string": _("Period"),
            },
        )
        groups = root.xpath("/search/group")
        if groups:
            groups[0].addprevious(separator)
            groups[0].addprevious(field)
        else:
            search = root.xpath("/search")
            search[0].append(separator)
            search[0].append(field)
        result["arch"] = etree.tostring(root, encoding="unicode")
        return result

    @api.model
    def get_views(self, views, options=None):
        """Adapt the label of the dummy search field

        Ensure the technical name does not show up in the Custom Filter
        fields list (while still showing up in the Export widget)
        """
        result = super().get_views(views, options=options)
        if "date_range_search_id" in result["models"][self._name]:
            result["models"][self._name]["date_range_search_id"]["string"] = _("Period")
        return result
