# Copyright 2020 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .mis_report import _is_valid_python_var


class ParentLoopError(ValidationError):
    pass


class InvalidNameError(ValidationError):
    pass


class MisReportSubReport(models.Model):
    _name = "mis.report.subreport"
    _description = "MIS Report - Sub Reports Relation"

    name = fields.Char(required=True)
    report_id = fields.Many2one(
        comodel_name="mis.report",
        required=True,
        ondelete="cascade",
    )
    subreport_id = fields.Many2one(
        comodel_name="mis.report",
        required=True,
        ondelete="restrict",
    )

    _sql_constraints = [
        (
            "name_unique",
            "unique(name, report_id)",
            "Subreport name should be unique by report",
        ),
        (
            "subreport_unique",
            "unique(subreport_id, report_id)",
            "Should not include the same report more than once as sub report "
            "of a given report",
        ),
    ]

    @api.constrains("name")
    def _check_name(self):
        for rec in self:
            if not _is_valid_python_var(rec.name):
                raise InvalidNameError(
                    _("Subreport name ({}) must be a valid python identifier").format(
                        rec.name
                    )
                )

    @api.constrains("report_id", "subreport_id")
    def _check_loop(self):
        def _has_subreport(reports, report):
            if not reports:
                return False
            if report in reports:
                return True
            return any(
                _has_subreport(r.subreport_ids.mapped("subreport_id"), report)
                for r in reports
            )

        for rec in self:
            if _has_subreport(rec.subreport_id, rec.report_id):
                raise ParentLoopError(_("Subreport loop detected"))

    # TODO check subkpi compatibility in subreports
