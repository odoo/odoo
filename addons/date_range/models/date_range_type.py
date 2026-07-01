# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
import logging

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, MONTHLY, WEEKLY, YEARLY

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DateRangeType(models.Model):
    _name = "date.range.type"
    _description = "Date Range Type"

    @api.model
    def _default_company(self):
        return self.env.company

    name = fields.Char(required=True, translate=True)
    allow_overlap = fields.Boolean(
        help="If set, date ranges of same type must not overlap.", default=False
    )
    active = fields.Boolean(
        help="The active field allows you to hide the date range type "
        "without removing it.",
        default=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company", index=1, default=_default_company
    )
    date_range_ids = fields.One2many("date.range", "type_id", string="Ranges")
    date_ranges_exist = fields.Boolean(compute="_compute_date_ranges_exist")

    # Defaults for generating date ranges
    name_expr = fields.Text(
        "Range name expression",
        help=(
            "Evaluated expression. E.g. "
            "\"'FY%s' % date_start.strftime('%Y%m%d')\"\nYou can "
            "use the Date types 'date_end' and 'date_start', as well as "
            "the 'index' variable."
        ),
    )
    range_name_preview = fields.Char(compute="_compute_range_name_preview", store=True)
    name_prefix = fields.Char("Range name prefix")
    duration_count = fields.Integer("Duration")
    unit_of_time = fields.Selection(
        [
            (str(YEARLY), "years"),
            (str(MONTHLY), "months"),
            (str(WEEKLY), "weeks"),
            (str(DAILY), "days"),
        ]
    )
    autogeneration_date_start = fields.Date(
        string="Autogeneration Start Date",
        help="Only applies when there are no date ranges of this type yet",
    )
    autogeneration_count = fields.Integer()
    autogeneration_unit = fields.Selection(
        [
            (str(YEARLY), "years"),
            (str(MONTHLY), "months"),
            (str(WEEKLY), "weeks"),
            (str(DAILY), "days"),
        ]
    )

    _sql_constraints = [
        (
            "date_range_type_uniq",
            "unique (name,company_id)",
            "A date range type must be unique per company !",
        )
    ]

    @api.constrains("company_id")
    def _check_company_id(self):
        if not self.env.context.get("bypass_company_validation", False):
            for rec in self.sudo():
                if not rec.company_id:
                    continue
                if bool(
                    rec.date_range_ids.filtered(
                        lambda r: r.company_id and r.company_id != rec.company_id
                    )
                ):
                    raise ValidationError(
                        _(
                            "You cannot change the company, as this "
                            "Date Range Type is assigned to Date Range '%s'."
                        )
                        % (rec.date_range_ids.display_name)
                    )

    @api.depends("name_expr", "name_prefix")
    def _compute_range_name_preview(self):
        year_start = fields.Datetime.now().replace(day=1, month=1)
        next_year = year_start + relativedelta(years=1)
        for dr_type in self:
            if dr_type.name_expr or dr_type.name_prefix:
                names = self.env["date.range.generator"]._generate_names(
                    [year_start, next_year], dr_type.name_expr, dr_type.name_prefix
                )
                dr_type.range_name_preview = names[0]
            else:
                dr_type.range_name_preview = False

    @api.depends("date_range_ids")
    def _compute_date_ranges_exist(self):
        for dr_type in self:
            dr_type.date_ranges_exist = bool(dr_type.date_range_ids)

    @api.onchange("name_expr")
    def onchange_name_expr(self):
        """Wipe the prefix if an expression is entered.

        The reverse is not implemented because we don't want to wipe the
        users' painstakingly crafted expressions by accident.
        """
        if self.name_expr and self.name_prefix:
            self.name_prefix = False

    @api.model
    def autogenerate_ranges(self):
        """Generate ranges for types with autogeneration settings"""
        logger = logging.getLogger(__name__)
        for dr_type in self.search(
            [
                ("autogeneration_count", "!=", False),
                ("autogeneration_unit", "!=", False),
                ("duration_count", "!=", False),
                ("unit_of_time", "!=", False),
            ]
        ):
            try:
                wizard = self.env["date.range.generator"].new({"type_id": dr_type.id})
                if not wizard.date_end:
                    # Nothing to generate
                    continue
                with self.env.cr.savepoint():
                    wizard.action_apply(batch=True)
            except Exception as e:
                logger.warning(
                    "Error autogenerating ranges for date range type "
                    "%s: %s" % (dr_type.name, e)
                )
