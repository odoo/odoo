from odoo import fields, models


class EventSponsorType(models.Model):
    _name = "event.sponsor.type"
    _description = "Event Sponsor Level"
    _order = "sequence"

    def _default_sequence(self):
        return (self.search([], order="sequence desc", limit=1).sequence or 0) + 1

    name = fields.Char(
        string="Sponsor Level",
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=_default_sequence)
    display_ribbon_style = fields.Selection(
        selection=[
            ("no_ribbon", "No Ribbon"),
            ("Gold", "Gold"),
            ("Silver", "Silver"),
            ("Bronze", "Bronze"),
        ],
        string="Ribbon Style",
        default="no_ribbon",
    )
