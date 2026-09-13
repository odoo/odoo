from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    deletion_delay = fields.Integer(
        default=30,
        config_parameter="document.deletion_delay",
        help="Delay after permanent deletion of the document in the trash (days)",
    )

    _check_deletion_delay = models.Constraint(
        "CHECK(deletion_delay >= 0)",
        "The deletion delay should be positive.",
    )
