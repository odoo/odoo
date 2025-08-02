from odoo import models, fields


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    def _work_address_id_domain(self):
        return [
            "|",
                "&",
                    "&",
                    ("type", "!=", "contact"),
                    ("type", "!=", "private"),
                ("id", "in", self.sudo().env.companies.partner_id.child_ids.ids),
            ("id", "in", self.sudo().env.companies.partner_id.ids),
        ]

    work_address_id = fields.Many2one(
        comodel_name="res.partner",
        string="Work Address",
        domain=lambda self: self._work_address_id_domain(),
    )
