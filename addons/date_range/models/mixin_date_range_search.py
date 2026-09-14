from lxml import etree

from odoo import api, fields, models
from odoo.fields import Domain

from odoo.addons.base.models.ir_ui_view_base import attach_ir

_NEGATIVE_OPERATORS = frozenset(
    (
        "!=",
        "<>",
        "not in",
        "not like",
        "not ilike",
        "not =like",
        "not =ilike",
        "not any",
        "not any!",
    )
)


class MixinDateRangeSearch(models.AbstractModel):
    """Adds a virtual period field that filters a model by predefined date ranges."""

    # To use: inherit "mixin.date.range.search" and set _date_range_search_field
    # to the model's date field. The field is auto-injected into search views and
    # translated into date comparisons by _search_date_range_search_id.
    _name = "mixin.date.range.search"
    _description = "Mixin class to add a Many2one style period search field"
    _date_range_search_field = "date"

    date_range_search_id = fields.Many2one(
        comodel_name="date.range",
        string="Filter by period (technical field)",
        compute="_compute_date_range_search_id",
        search="_search_date_range_search_id",
    )

    def _compute_date_range_search_id(self):
        """Return False; the field exists only to expose a search widget."""
        for record in self:
            record.date_range_search_id = False

    @api.model
    def _is_negative_operator(self, operator):
        """Return whether the operator excludes rather than includes matches.

        :param str operator: domain operator to test
        :rtype: bool
        """
        return operator in _NEGATIVE_OPERATORS

    @api.model
    def _search_date_range_search_id(self, operator, value):
        """Translate a period selection into a domain on the model's date field.

        Multiple ranges are combined with OR logic; negative operators invert
        the match and edge cases return Domain.TRUE/FALSE.

        :param str operator: search operator ('=', '!=', 'in', 'not in', ...)
        :param value: range name (str), id (int), list of ids, or bool
        :return: domain filtering records by the selected range(s)
        :rtype: list or odoo.fields.Domain
        """
        # Odoo 19's domain optimizer normalizes ``('field', '=', X)``
        # to ``('field', 'in', OrderedSet((X,)))`` before dispatching to
        # search methods (see _optimize_equal_as_in in
        # core/odoo/orm/domain/optimizations.py). The value for
        # ``= True`` / ``= False`` therefore arrives here as a single-
        # element collection containing a bool, NOT as a scalar. Unwrap
        # any single-element collection whose sole element is a bool so
        # the "all records / no records" branches below behave as
        # intended. Without this we fall through to a date.range search
        # with a boolean id, which PostgreSQL rejects with
        # "operator does not exist: integer = boolean".
        if (
            not isinstance(value, (str, bytes))
            and hasattr(value, "__iter__")
            and not isinstance(value, bool)
        ):
            value_list = list(value)
            if len(value_list) == 1 and isinstance(value_list[0], bool):
                value = value_list[0]

        # Deal with some bogus values
        if not value:
            if self._is_negative_operator(operator):
                return Domain.TRUE
            return Domain.FALSE
        if value is True:
            if self._is_negative_operator(operator):
                return Domain.FALSE
            return Domain.TRUE
        # Assume from here on that the value is a string,
        # a single id or a list of ids
        ranges = self.env["date.range"]
        if isinstance(value, str):
            ranges = self.env["date.range"].search([("name", operator, value)])
        else:
            # bool is a subclass of int in Python; guard against
            # isinstance(True, int) wrapping a stray boolean into [True].
            if isinstance(value, int) and not isinstance(value, bool):
                value = [value]
            sub_op = "not in" if self._is_negative_operator(operator) else "in"
            ranges = self.env["date.range"].search([("id", sub_op, value)])
        if not ranges:
            return Domain.FALSE
        field = self._date_range_search_field
        return Domain.OR(
            Domain(field, ">=", date_range.date_start)
            & Domain(field, "<=", date_range.date_end)
            for date_range in ranges
        )

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        """Inject the period search field into search views that omit it.

        The field is inserted before the first group element, or appended when
        no groups exist, and is skipped if already declared explicitly.

        :param int view_id: id of the view to retrieve
        :param str view_type: view type; only 'search' is modified
        :return: view definition, arch amended for search views
        :rtype: dict
        """
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
                "string": self.env._("Period"),
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
        return attach_ir(result)

    @api.model
    def get_views(self, views, options=None):
        """Relabel the technical period field to "Period" in returned views.

        :param list views: (view_id, view_type) tuples to retrieve
        :param dict options: extra view-retrieval options
        :return: view definitions with the corrected field label
        :rtype: dict
        """
        result = super().get_views(views, options=options)
        if "date_range_search_id" in result["models"][self._name]["fields"]:
            result["models"][self._name]["fields"]["date_range_search_id"]["string"] = (
                self.env._("Period")
            )
        return result
