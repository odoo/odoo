import datetime
from itertools import starmap

from odoo import api, fields, models
from odoo.fields import Domain

_CLASSIFYING_FIELDS = frozenset({"min_value", "max_value", "active"})

_FIRST_YEAR = datetime.date.min.year
_LAST_YEAR = datetime.date.max.year


class ResPartnerAgeRange(models.Model):
    _name = "res.partner.age.range"
    _inherit = ["mixin.band"]
    _description = "Partner Age Range"
    _order = "min_value, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    min_value = fields.Float(
        string="From year",
        digits=(16, 0),
        default=lambda self: self._default_min_value(),
        help="First birth year of the cohort, inclusive.",
    )
    max_value = fields.Float(
        string="To year",
        digits=(16, 0),
        help="First birth year *after* the cohort -- it is the lower bound of "
        "the next one. 0 means no upper limit, which the newest cohort should "
        "use so a newborn still classifies. The oldest cohort stays closed on "
        "its lower side: a birth year before it predates every cohort here.",
    )
    partner_count = fields.Integer(
        string="Contacts",
        compute="_compute_partner_count",
    )
    gap_before = fields.Char(
        string="Uncovered",
        compute="_compute_gap_before",
        help="Birth years left between this cohort and the one below it. A "
        "contact born in those years is classified into nothing at all, which "
        "the scale gives no other sign of.",
    )

    _name_uniq = models.UniqueIndex(
        "(lower(name))", "A cohort with the same name already exists."
    )

    @api.model_create_multi
    def create(self, vals_list):
        ranges = super().create(vals_list)
        ranges._add_partners_to_compute(ranges._current_spans())
        return ranges

    def write(self, vals):
        if _CLASSIFYING_FIELDS.isdisjoint(vals):
            return super().write(vals)
        spans = self._current_spans()
        result = super().write(vals)
        self._add_partners_to_compute(spans + self._current_spans())
        return result

    def unlink(self):
        spans = self._current_spans()
        result = super().unlink()
        self._add_partners_to_compute(spans)
        return result

    @api.depends("name", "min_value", "max_value")
    def _compute_display_name(self) -> None:
        # The bounds are half-open years and TRAPS.md exists mostly because
        # that is easy to get backwards. Naming the years a cohort actually
        # contains puts the answer on the record that raises the question.
        for band in self:
            first, last = int(band.min_value), int(band.max_value) - 1
            if band.max_value and band.min_value:
                span = self.env._("%(first)s-%(last)s", first=first, last=last)
            elif band.max_value:
                span = self.env._("up to %(last)s", last=last)
            elif band.min_value:
                span = self.env._("%(first)s and later", first=first)
            else:
                span = ""
            band.display_name = (
                f"{band.name} ({span})" if band.name and span else band.name
            )

    def _compute_partner_count(self) -> None:
        counts = dict(
            self.env["res.partner"]._read_group(
                [("age_range_id", "in", self.ids)], ["age_range_id"], ["__count"]
            )
        )
        for band in self:
            band.partner_count = counts.get(band, 0)

    @api.depends("min_value", "max_value", "active")
    def _compute_gap_before(self) -> None:
        scale = self.search([])
        for band in self:
            closed_below = scale.filtered(
                lambda other, band=band: (
                    other.max_value and other.max_value <= band.min_value
                )
            )
            highest = max(closed_below.mapped("max_value"), default=band.min_value)
            band.gap_before = (
                self.env._(
                    "%(first)s-%(last)s",
                    first=int(highest),
                    last=int(band.min_value) - 1,
                )
                if band.active and highest < band.min_value
                else False
            )

    def action_open_partners(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": self.display_name,
            "res_model": "res.partner",
            "view_mode": "list,kanban,form",
            "domain": [("age_range_id", "=", self.id)],
        }

    def _current_spans(self):
        return [(band.min_value, band.max_value) for band in self]

    @staticmethod
    def _span_domain(min_value, max_value):
        domain = Domain("birthdate", "!=", False)
        if (first_year := int(min_value)) > _FIRST_YEAR:
            domain &= Domain("birthdate", ">=", datetime.date(first_year, 1, 1))
        if _FIRST_YEAR < (next_year := int(max_value)) <= _LAST_YEAR:
            domain &= Domain("birthdate", "<", datetime.date(next_year, 1, 1))
        return domain

    def _add_partners_to_compute(self, spans):
        domain = Domain.OR(starmap(self._span_domain, spans))
        if self.ids:
            domain |= Domain("age_range_id", "in", self.ids)
        # sudo() carries privileges, not active_test: without it an archived
        # partner is skipped by every sweep and keeps a cohort no bound supports.
        partners = (
            self.env["res.partner"]
            .sudo()
            .with_context(active_test=False)
            .search(domain)
        )
        if partners:
            self.env.add_to_compute(partners._fields["age_range_id"], partners)
        # gap_before reads the whole scale and partner_count reads the whole
        # address book, so neither can be expressed as a dependency on the
        # record's own fields. This is the one chokepoint every create, write
        # and unlink passes through, so it is where their cache is dropped --
        # without it a band still reports a gap the band below it just closed.
        self.invalidate_model(["gap_before", "partner_count"])

    def _default_min_value(self):
        # Where the scale currently ends. The newest cohort is the one meant to
        # stay open-ended, and its max_value of 0 means "no upper limit" -- but
        # 0 as a LOWER bound means "no lower limit", the opposite reading, so
        # chaining onto it proposed an open-below cohort on exactly the scales
        # that were built correctly. Chain onto the highest closed bound
        # instead: appending past an open cohort has to close it first, and the
        # overlap error says so by name.
        newest_closed = self.search(
            [("max_value", "!=", 0)], order="max_value desc", limit=1
        )
        return newest_closed.max_value if newest_closed else 0.0
