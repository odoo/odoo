from odoo import fields, models


class ApprovalObservation(models.Model):
    """One row per gated call let through while its gate is only watching.

    Written by an `approval.binding` in Observe mode and by a document gate whose
    checkpoint is not enforcing yet. Append-only on purpose.

    Append-only on purpose. A counter on the binding would have been smaller,
    but every gated call would then contend for the same row's lock, and the
    question this table exists to answer -- who is reaching this operation,
    and how many of them arrive elevated -- needs the breakdown, not a total.
    """

    _name = "approval.observation"
    _description = "Approval Observation"
    _order = "id desc"

    binding_id = fields.Many2one(
        comodel_name="approval.binding",
        index="btree_not_null",
        ondelete="cascade",
        help="The configured gate that observed the call, when one did. Empty for a "
        "gate a model declares in code.",
    )
    model_name = fields.Char(
        string="Model",
        index=True,
        required=True,
    )
    operation = fields.Char(
        index=True,
        required=True,
        help="The gated method the call was reaching.",
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
        index=True,
        required=True,
        help="`sudo()` keeps `uid`, so a caller elevated by sudo() is "
        "distinguishable from the real superuser. The two are different "
        "risks and the point of observing is to count them separately.",
    )
    would_block = fields.Boolean(
        help="Whether this call would have been refused had the gate been "
        "enforcing. This is the number that decides whether switching it "
        "on is a small correction or a large one."
    )
    date = fields.Datetime(
        default=fields.Datetime.now,
        index=True,
    )
