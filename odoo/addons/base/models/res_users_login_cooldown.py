from odoo import fields, models


class ResUsersLoginCooldown(models.Model):
    _name = "res.users.login.cooldown"
    _description = "Login Failure Cooldown"
    _log_access = False

    source = fields.Char(
        index="btree",
        required=True,
    )
    failures = fields.Integer(
        default=0,
        required=True,
    )
    last_failure = fields.Datetime(
        index="btree",
        required=True,
    )

    _source_uniq = models.Constraint(
        "unique (source)",
        "There can be only one cooldown row per source.",
    )
