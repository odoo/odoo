from odoo import fields, models

from odoo.addons.base.models.mixin_recurrence_interval import (
    REPEAT_UNIT_SELECTION,  # noqa: F401  re-exported: consumers take the whole vocabulary from the rule
)

REPEAT_TYPE_SELECTION = [
    ("forever", "Forever"),
    ("until", "Until"),
]

REPEAT_TYPE_COUNT = ("count", "Number of Repetitions")


class MixinRecurrenceRule(models.AbstractModel):
    _name = "mixin.recurrence.rule"
    _description = "Recurrence Rule Mixin"
    _inherit = ["mixin.recurrence.interval"]

    repeat_type = fields.Selection(
        selection=REPEAT_TYPE_SELECTION,
        string="Until",
        export_string_translation=False,
        default="forever",
    )
