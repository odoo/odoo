from odoo import fields, models

RECURRENCE_UPDATE_SELECTION = [
    ("this", "This one"),
    ("subsequent", "This and the following ones"),
    ("all", "All of them"),
]


class MixinRecurrenceOccurrence(models.AbstractModel):
    _name = "mixin.recurrence.occurrence"
    _description = "Recurrence Occurrence Mixin"

    recurrence_update = fields.Selection(
        selection=RECURRENCE_UPDATE_SELECTION,
        default="this",
        store=False,
        copy=False,
    )
