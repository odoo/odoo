from odoo import api, fields, models


class ResourceTimeType(models.Model):
    _name = "resource.time.type"
    _description = "Kind of Time"
    _order = "sequence, id"

    name = fields.Char(
        translate=True,
        required=True,
    )
    active = fields.Boolean(default=True)
    code = fields.Char(
        required=True,
        help="The stable name migrations and code refer to this kind by.",
    )
    sequence = fields.Integer(default=10)
    is_work = fields.Boolean(
        string="Counts as Working Time",
        default=False,
        help="Time of this kind stays in the working schedule. Unset, it is an absence and the schedule subtracts it.",
    )

    _code_uniq = models.Constraint(
        "UNIQUE(code)",
        "Two kinds of time cannot share a code.",
    )

    @api.model
    def _get_leave_type(self):
        """The kind an absence has, and the one a schedule subtracts."""
        return self.env.ref("resource.time_type_leave", raise_if_not_found=False)

    @api.model
    def _get_work_type(self):
        return self.env.ref("resource.time_type_work", raise_if_not_found=False)
