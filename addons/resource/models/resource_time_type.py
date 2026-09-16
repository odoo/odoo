from odoo import api, fields, models


class ResourceTimeType(models.Model):
    """What a stretch of time counts as, for the schedule that reads it.

    The kernel asks one question of a kind of time: does it come out of working
    time or not. That is the whole of what `resource` reads -- a schedule
    subtracts its exceptions whose kind is an absence, and leaves the rest alone.

    Everything a payroll knows about a kind of time -- what it pays, at what rate,
    which code it exports under, which country invented it -- belongs to the model
    that pays it. `hr.work.entry.type` names one of these to say which kind of time
    it is, and keeps the rest to itself, because `resource` is reached by a
    thousand modules that never install `hr`.

    Two records ship, because two is what the kernel distinguishes. A deployment
    that wants "Training" or "Standby" adds them with `is_work` set the way its
    schedule should read them; nothing in the kernel counts the records.
    """

    _name = "resource.time.type"
    _description = "Kind of Time"
    _order = "sequence, id"

    name = fields.Char(
        translate=True,
        required=True,
    )
    code = fields.Char(
        required=True,
        help="The stable name migrations and code refer to this kind by.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
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
