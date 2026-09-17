import logging
import operator as operator_module
from collections import defaultdict
from datetime import UTC

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.intervals import Intervals
from odoo.tools import SQL
from odoo.tools.date_utils import get_intervals_hours, localized

from .utils import peak_capacity

_logger = logging.getLogger(__name__)

COMPARATORS = {
    "=": operator_module.eq,
    "!=": operator_module.ne,
    "<": operator_module.lt,
    "<=": operator_module.le,
    ">": operator_module.gt,
    ">=": operator_module.ge,
}


class ResourceReservation(models.Model):
    _name = "resource.reservation"
    _description = "Resource Reservation"
    _inherit = ["mixin.resource.scheduling.tools", "mixin.resource.ledger"]
    _order = "date_start"
    _check_company_auto = True

    _OVERLAP_SWEEP_FIELDS = [
        "date_start",
        "date_end",
        "resource_id",
        "allocated_percentage",
        "active",
    ]

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        precompute=True,
        store=True,
        index="btree_not_null",
        readonly=False,
    )

    date_start = fields.Datetime(
        string="Scheduled Start",
        index=True,
    )
    date_end = fields.Datetime(
        string="Scheduled End",
        index=True,
    )

    resource_id = fields.Many2one(
        comodel_name="resource.resource",
        index=True,
        check_company=True,
        help="The resource (person, equipment) assigned to this schedule.",
    )
    resource_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Working Calendar",
        compute="_compute_resource_calendar_id",
        store=True,
        readonly=False,
        check_company=True,
    )

    allocated_hours = fields.Float(
        compute="_compute_allocated_hours",
        store=True,
        readonly=False,
        help="Working hours between start and end, respecting the resource calendar.",
    )
    allocated_percentage = fields.Float(
        string="Allocation %",
        default=100.0,
        help="Percentage of the resource's work capacity allocated to this schedule.",
    )
    _check_allocated_percentage = models.Constraint(
        "CHECK(allocated_percentage IS NOT NULL"
        " AND allocated_percentage >= 0 AND allocated_percentage < 'Infinity'::float8)",
        "Allocation % must be finite and nonnegative.",
    )

    schedule_overlap_count = fields.Integer(
        string="Scheduling Conflicts",
        compute="_compute_schedule_overlap_count",
        search="_search_schedule_overlap_count",
    )

    peak_booking_percentage = fields.Float(
        string="Peak Booking %",
        compute="_compute_booking_load",
    )
    booking_state = fields.Selection(
        selection=[
            ("under", "Underbooked"),
            ("full", "Fully Booked"),
            ("over", "Overbooked"),
            ("exceeded", "Ceiling Exceeded"),
        ],
        string="Booking Status",
        compute="_compute_booking_load",
    )

    res_model = fields.Char(
        string="Source Model",
        index=True,
        readonly=True,
        help="Technical name of the model that created this reservation.",
    )
    res_id = fields.Many2oneReference(
        model_field="res_model",
        string="Source Record",
        index=True,
        readonly=True,
        help="ID of the record in the source model.",
    )

    enforcement_mode = fields.Selection(
        selection=[("soft", "Warning"), ("hard", "Block")],
        default="soft",
        required=True,
        help="Warning permits excess capacity unless the resource enforces its ceiling. Block prevents total simultaneous allocation from exceeding the resource ceiling.",
    )

    origin_display = fields.Char(
        string="Source",
        compute="_compute_origin_display",
    )

    _resource_schedule_idx = models.Index("(resource_id, date_start, date_end)")
    _origin_idx = models.Index("(res_model, res_id)")

    @api.constrains("date_start", "date_end")
    def _check_date_sanity(self):
        for record in self:
            if (
                record.date_start
                and record.date_end
                and record.date_start > record.date_end
            ):
                raise ValidationError(
                    self.env._(
                        "%(name)s: start date must be before end date.",
                        name=record.name,
                    )
                )

    @api.constrains(
        "date_start",
        "date_end",
        "resource_id",
        "allocated_percentage",
        "active",
        "enforcement_mode",
    )
    def _check_hard_overlap(self):
        live = self.filtered(
            lambda r: r.active and r.resource_id and r.date_start and r.date_end
        )
        hard = live.filtered_domain(self._enforced_booking_domain())

        if live:
            live.resource_id._lock_for_scheduling()

        if live:
            windows_by_resource = defaultdict(lambda: [None, None])
            for record in live:
                window = windows_by_resource[record.resource_id.id]
                window[0] = (
                    record.date_start
                    if window[0] is None
                    else min(window[0], record.date_start)
                )
                window[1] = (
                    record.date_end
                    if window[1] is None
                    else max(window[1], record.date_end)
                )
            hard |= (
                self.sudo()
                .search(
                    Domain.AND(
                        [
                            Domain("id", "not in", live.ids),
                            Domain("active", "=", True),
                            self._enforced_booking_domain(),
                            Domain.OR(
                                Domain.AND(
                                    [
                                        Domain("resource_id", "=", resource_id),
                                        Domain("date_start", "<", end),
                                        Domain("date_end", ">", start),
                                    ]
                                )
                                for resource_id, (
                                    start,
                                    end,
                                ) in windows_by_resource.items()
                            ),
                        ]
                    )
                )
                .with_env(self.env)
            )
        if not hard:
            return
        hard._compute_booking_load()
        for record in hard:
            if (
                record.peak_booking_percentage
                > record.resource_id.booking_limit_percentage + 1e-7
            ):
                raise ValidationError(
                    self.env._(
                        "%(name)s: %(resource)s exceeds its configured booking ceiling during this time.",
                        name=record.name,
                        resource=record.resource_id.name,
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.invalidate_model(
            ["peak_booking_percentage", "booking_state", "schedule_overlap_count"]
        )
        return records

    def write(self, vals):
        if set(vals) & set(self._OVERLAP_SWEEP_FIELDS):
            resources = self.resource_id
            if vals.get("resource_id"):
                resources |= self.env["resource.resource"].browse(vals["resource_id"])
            resources._lock_for_scheduling()
        result = super().write(vals)
        self.invalidate_model(
            ["peak_booking_percentage", "booking_state", "schedule_overlap_count"]
        )
        return result

    def unlink(self):
        self.resource_id._lock_for_scheduling()
        result = super().unlink()
        self.invalidate_model(
            ["peak_booking_percentage", "booking_state", "schedule_overlap_count"]
        )
        return result

    @api.depends("resource_id.company_id")
    def _compute_company_id(self):
        for record in self:
            record.company_id = (
                record.resource_id.company_id or record.company_id or self.env.company
            )

    @api.depends(
        "resource_id",
        "resource_id.booking_limit_percentage",
        "date_start",
        "date_end",
        "allocated_percentage",
        "active",
    )
    def _compute_booking_load(self):
        dated = self.filtered(
            lambda r: r.active and r.resource_id and r.date_start and r.date_end
        )
        loads = (
            self._booking_load_batch(
                dated.resource_id,
                min(dated.mapped("date_start")),
                max(dated.mapped("date_end")),
            )
            if dated
            else {}
        )
        for record in self:
            peak = (
                peak_capacity(
                    loads.get(record.resource_id.id, []),
                    record.date_start,
                    record.date_end,
                )
                if record in dated
                else 0.0
            )
            record.peak_booking_percentage = peak
            if peak > record.resource_id.booking_limit_percentage + 1e-7:
                record.booking_state = "exceeded"
            elif peak > 100 + 1e-7:
                record.booking_state = "over"
            elif peak >= 100 - 1e-7:
                record.booking_state = "full"
            else:
                record.booking_state = "under"

    @api.depends("resource_id", "resource_id.calendar_id", "company_id")
    def _compute_resource_calendar_id(self):
        for record in self:
            calendar = record.resource_id.calendar_id
            company = record.company_id or record.env.company
            if calendar and calendar.company_id and calendar.company_id != company:
                calendar = calendar.browse()
            record.resource_calendar_id = calendar or company.resource_calendar_id

    @api.depends(
        "date_start",
        "date_end",
        "resource_id",
        "resource_calendar_id",
        "allocated_percentage",
    )
    def _compute_allocated_hours(self):
        self = self.with_context(resource_capacity_aware=True)
        undated = self.filtered(lambda r: not r.date_start or not r.date_end)
        undated.allocated_hours = 0.0
        dated = self - undated
        if not dated:
            return

        flexible = dated.filtered(
            lambda r: r.resource_id and r.resource_id._is_flexible()
        )
        for record in flexible:
            record.allocated_hours = record._scale_allocation(
                record._scheduling_get_work_hours(
                    record.date_start,
                    record.date_end,
                    resource=record.resource_id,
                    calendar=record.resource_calendar_id,
                )
            )

        groups = defaultdict(self.browse)
        for record in dated - flexible:
            groups[record.resource_calendar_id] |= record

        attendance = self.env["resource.calendar.attendance"]
        for calendar, records in groups.items():
            window_start = localized(min(records.mapped("date_start")))
            window_end = localized(max(records.mapped("date_end")))

            if calendar:
                native = records.resource_id.filtered(
                    lambda resource, calendar=calendar: resource.calendar_id == calendar
                )
            else:
                native = records.resource_id
            overridden = records.resource_id - native
            intervals_per_resource = {}
            if native:
                intervals_per_resource, _calendar_intervals = (
                    native._get_valid_work_intervals(window_start, window_end)
                )
            if overridden and calendar:
                intervals_per_resource.update(
                    calendar._work_intervals_batch(
                        window_start, window_end, resources=overridden
                    )
                )
            calendar_intervals = None
            if len(records.filtered(lambda r: not r.resource_id)) and calendar:
                calendar_intervals = calendar._work_intervals_batch(
                    window_start, window_end
                )[False]

            for record in records:
                if record.resource_id:
                    intervals = intervals_per_resource.get(record.resource_id.id)
                elif calendar_intervals is not None:
                    intervals = calendar_intervals
                else:
                    span = localized(record.date_end) - localized(record.date_start)
                    record.allocated_hours = record._scale_allocation(
                        span.total_seconds() / 3600.0
                    )
                    continue
                clipped = (intervals or Intervals()) & Intervals(
                    [
                        (
                            localized(record.date_start),
                            localized(record.date_end),
                            attendance,
                        )
                    ]
                )
                record.allocated_hours = record._scale_allocation(
                    get_intervals_hours(clipped)
                )

    @api.depends(
        "date_start", "date_end", "resource_id", "allocated_percentage", "active"
    )
    def _compute_schedule_overlap_count(self):
        conflicts = self._conflicting_reservations()
        for record in self:
            record.schedule_overlap_count = len(conflicts[record.id])

    @api.depends("res_model", "res_id")
    def _compute_origin_display(self):
        self.origin_display = False
        with_origin = self.filtered(lambda r: r.res_model and r.res_id)
        for model_name, records in with_origin.grouped("res_model").items():
            if model_name not in self.env:
                for record in records:
                    record.origin_display = f"{model_name},{record.res_id}"
                continue
            sources = (
                self.env[model_name]
                .browse(records.mapped("res_id"))
                .exists()
                ._filtered_access("read")
            )
            names = dict(zip(sources.ids, sources.mapped("display_name"), strict=True))
            for record in records:
                record.origin_display = names.get(record.res_id) or (
                    f"{model_name},{record.res_id}"
                )

    def _scale_allocation(self, work_hours):
        self.check_singleton()
        return round(work_hours * self.allocated_percentage / 100.0, 2)

    @api.model
    def _enforced_booking_domain(self):
        return Domain.OR(
            [
                Domain("enforcement_mode", "=", "hard"),
                Domain("resource_id.enforce_booking_limit", "=", True),
            ]
        )

    @api.model
    def _booking_load_batch(self, resources, start, stop, domain=None):
        bookings = self.sudo().search_fetch(
            Domain.AND(
                [
                    Domain("resource_id", "in", resources.ids),
                    Domain("active", "=", True),
                    Domain("date_start", "<", stop),
                    Domain("date_end", ">", start),
                    Domain(domain or []),
                ]
            ),
            ["resource_id", "date_start", "date_end", "allocated_percentage"],
        )
        result = {resource.id: [] for resource in resources}
        for booking in bookings:
            result[booking.resource_id.id].append(
                (
                    booking.date_start,
                    booking.date_end,
                    booking.allocated_percentage,
                )
            )
        return result

    def _conflicting_reservations(self):
        stored = self.filtered(
            lambda r: (
                r.id
                and isinstance(r.id, int)
                and r.resource_id
                and r.date_start
                and r.date_end
            )
        )
        empty = self.browse()
        result = dict.fromkeys(self._ids, empty)
        if not stored:
            return result

        self.flush_model(self._OVERLAP_SWEEP_FIELDS)
        partners = self._overlap_partners(
            (
                SQL("AND resource_id = ANY(%s)", list(set(stored.resource_id.ids))),
                SQL("AND date_start < %s", max(stored.mapped("date_end"))),
                SQL("AND date_end > %s", min(stored.mapped("date_start"))),
            )
        )
        for record in stored:
            result[record.id] = self.browse(sorted(partners.get(record.id, ())))
        return result

    @api.model
    def _prospective_conflicts(self, vals_list, ignore_ids=()):
        prospective = []
        for index, vals in enumerate(vals_list):
            resource_id = vals.get("resource_id")
            date_start, date_end = vals.get("date_start"), vals.get("date_end")
            if not resource_id or not date_start or not date_end:
                continue
            date_start = fields.Datetime.to_datetime(date_start)
            date_end = fields.Datetime.to_datetime(date_end)
            if date_end <= date_start:
                continue
            pct = vals.get("allocated_percentage")
            pct = 100.0 if pct is None else max(0.0, pct)
            prospective.append((-(index + 1), resource_id, date_start, date_end, pct))
        if not prospective:
            return self.browse()

        self.flush_model(self._OVERLAP_SWEEP_FIELDS)
        conditions = [
            SQL("AND resource_id = ANY(%s)", list({row[1] for row in prospective})),
            SQL("AND date_start < %s", max(row[3] for row in prospective)),
            SQL("AND date_end > %s", min(row[2] for row in prospective)),
        ]
        if ignore_ids:
            conditions.append(SQL("AND id != ALL(%s)", list(ignore_ids)))
        partners = self._overlap_partners(tuple(conditions), prospective)
        conflicting = set()
        for sentinel, *_rest in prospective:
            conflicting.update(peer for peer in partners.get(sentinel, ()) if peer > 0)
        return self.browse(sorted(conflicting))

    @api.model
    def _search_schedule_overlap_count(self, operator, value):
        if operator not in COMPARATORS or not isinstance(value, int):
            return NotImplemented
        compare = COMPARATORS[operator]

        self.flush_model(self._OVERLAP_SWEEP_FIELDS)
        conflicted = {
            res_id: len(peers) for res_id, peers in self._overlap_partners().items()
        }

        if compare(0, value):
            excluded = [
                res_id
                for res_id, count in conflicted.items()
                if not compare(count, value)
            ]
            return [("id", "not in", excluded)]
        return [
            (
                "id",
                "in",
                [
                    res_id
                    for res_id, count in conflicted.items()
                    if compare(count, value)
                ],
            )
        ]

    def _overlap_partners(self, extra_conditions=(), prospective=()):
        rows = SQL(
            """
            SELECT id, resource_id, date_start, date_end,
                   GREATEST(0, COALESCE(allocated_percentage, 100))::float8
              FROM %s
             WHERE resource_id IS NOT NULL
               AND active
               AND date_start IS NOT NULL
               AND date_end IS NOT NULL
               AND date_end > date_start
               %s
            """,
            SQL.identifier(self._table),
            SQL(" ").join(extra_conditions),
        )
        if prospective:
            rows = SQL(
                "%s UNION ALL SELECT * FROM (VALUES %s)"
                " AS prospective(id, resource_id, date_start, date_end, pct)",
                rows,
                SQL(", ").join(
                    SQL(
                        "(%s::int, %s::int, %s::timestamp, %s::timestamp, %s::float8)",
                        *row,
                    )
                    for row in prospective
                ),
            )
        self.env.cr.execute(
            SQL(
                """
                WITH booking(id, resource_id, date_start, date_end, pct) AS (%s),
                     event AS (
                         SELECT resource_id, date_start AS instant, 1 AS kind, pct
                           FROM booking
                          UNION ALL
                         SELECT resource_id, date_end, 0, -pct
                           FROM booking
                     ),
                     load AS (
                         SELECT resource_id, instant, kind,
                                SUM(pct) OVER (
                                    PARTITION BY resource_id
                                    ORDER BY instant, kind
                                    ROWS UNBOUNDED PRECEDING
                                ) AS total
                           FROM event
                     ),
                     hot AS (
                         SELECT DISTINCT resource_id, instant
                           FROM load
                          WHERE kind = 1 AND total > 100
                     )
                SELECT this.id, ARRAY_AGG(DISTINCT other.id)
                  FROM hot
                  JOIN booking AS this
                    ON this.resource_id = hot.resource_id
                   AND this.date_start <= hot.instant
                   AND this.date_end > hot.instant
                  JOIN booking AS other
                    ON other.resource_id = hot.resource_id
                   AND other.id <> this.id
                   AND other.date_start <= hot.instant
                   AND other.date_end > hot.instant
                 GROUP BY this.id
                """,
                rows,
            )
        )
        return {res_id: set(peers) for res_id, peers in self.env.cr.fetchall()}

    @api.autovacuum
    def _gc_orphan_reservations(self):
        reservations = self.sudo().with_context(active_test=False)
        model_names = [
            res_model
            for [res_model] in reservations._read_group(
                [("res_model", "!=", False)], groupby=["res_model"]
            )
        ]
        orphan_ids = []
        for model_name in model_names:
            model = self.env.get(model_name)
            if model is None or not model._auto:
                orphan_ids.extend(
                    reservations.search([("res_model", "=", model_name)]).ids
                )
                continue
            self.env.cr.execute(
                SQL(
                    """
                    SELECT reservation.id
                      FROM %s AS reservation
                 LEFT JOIN %s AS source ON source.id = reservation.res_id
                     WHERE reservation.res_model = %s
                       AND source.id IS NULL
                    """,
                    SQL.identifier(self._table),
                    SQL.identifier(model._table),
                    model_name,
                )
            )
            orphan_ids.extend(row[0] for row in self.env.cr.fetchall())

        if orphan_ids:
            _logger.info(
                "Garbage-collecting %s orphan resource.reservation record(s)",
                len(orphan_ids),
            )
            reservations.browse(orphan_ids).unlink()

    def action_view_origin(self):
        self.check_singleton()
        if not self.res_model or not self.res_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            "views": [(False, "form")],
            "target": "current",
        }

    @api.model
    def _reservation_intervals_batch(self, start_dt, end_dt, resources, domain=None):
        if not resources:
            return {}

        base_domain = [
            ("resource_id", "in", resources.ids),
            ("date_start", "<", end_dt.astimezone(UTC).replace(tzinfo=None)),
            ("date_end", ">", start_dt.astimezone(UTC).replace(tzinfo=None)),
            ("active", "=", True),
        ]
        if domain:
            base_domain = Domain(base_domain) & Domain(domain)

        tuples_by_resource = defaultdict(list)
        for res in self.sudo().search(base_domain):
            tuples_by_resource[res.resource_id.id].append(
                (localized(res.date_start), localized(res.date_end), res)
            )

        return {
            resource.id: Intervals(tuples_by_resource.get(resource.id, []))
            for resource in resources
        }
