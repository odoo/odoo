from odoo import fields, models


class ApprovalBindingObservation(models.Model):
    """One row per gated call, written by a binding in Observe mode.

    Append-only on purpose. A counter on the binding would have been smaller,
    but every gated call would then contend for the same row's lock, and the
    question this table exists to answer -- who is reaching this operation,
    and how many of them arrive elevated -- needs the breakdown, not a total.
    """

    _name = "approval.binding.observation"
    _description = "Approval Binding Observation"
    _order = "id desc"

    binding_id = fields.Many2one(
        comodel_name="approval.binding",
        index=True,
        required=True,
        ondelete="cascade",
    )
    res_id = fields.Integer(
        string="Record ID",
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        index=True,
    )
    elevation = fields.Selection(
        selection=[
            ("none", "Not elevated"),
            ("superuser", "Superuser"),
            ("self_elevated", "Elevated by sudo()"),
        ],
        help="`sudo()` keeps `uid`, so a caller elevated by sudo() is "
        "distinguishable from the real superuser. The two are different "
        "risks and the point of observing is to count them separately.",
        index=True,
        required=True,
    )
    would_block = fields.Boolean(
        help="Whether this call would have been refused had the binding been "
        "in Block mode. This is the number that decides whether switching it "
        "on is a small correction or a large one."
    )
    date = fields.Datetime(
        default=fields.Datetime.now,
        index=True,
    )
