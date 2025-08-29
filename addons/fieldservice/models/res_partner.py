# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    type = fields.Selection(selection_add=[("fsm_location", "Location")])
    fsm_location = fields.Boolean("Is a FS Location")
    fsm_person = fields.Boolean("Is a FS Worker")
    fsm_location_id = fields.One2many(
        comodel_name="fsm.location",
        string="Related FS Location",
        inverse_name="partner_id",
        readonly=True,
    )
    service_location_id = fields.Many2one(
        "fsm.location", string="Primary Service Location"
    )
    owned_location_ids = fields.One2many(
        "fsm.location",
        "owner_id",
        string="Owned Locations",
        domain=[("fsm_parent_id", "=", False)],
    )
    owned_location_count = fields.Integer(
        compute="_compute_owned_location_count", string="# of Owned Locations"
    )

    def _compute_owned_location_count(self):
        for partner in self:
            partner.owned_location_count = self.env["fsm.location"].search_count(
                [("owner_id", "child_of", partner.id)]
            )

    def action_open_owned_locations(self):
        for partner in self:
            owned_location_ids = self.env["fsm.location"].search(
                [("owner_id", "child_of", partner.id)]
            )
            action = self.env.ref("fieldservice.action_fsm_location").sudo().read()[0]
            action["context"] = {}
            if len(owned_location_ids) > 1:
                action["domain"] = [("id", "in", owned_location_ids.ids)]
            elif len(owned_location_ids) == 1:
                action["views"] = [
                    (self.env.ref("fieldservice.fsm_location_form_view").id, "form")
                ]
                action["res_id"] = owned_location_ids.ids[0]
            return action

    def _convert_fsm_location(self):
        wiz = self.env["fsm.wizard"]
        partners_with_loc_ids = (
            self.env["fsm.location"]
            .sudo()
            .search([("active", "in", [False, True]), ("partner_id", "in", self.ids)])
            .mapped("partner_id")
        ).ids

        partners_to_convert = self.filtered(
            lambda p: p.type == "fsm_location" and p.id not in partners_with_loc_ids
        )
        for partner_to_convert in partners_to_convert:
            wiz.action_convert_location(partner_to_convert)

    def write(self, value):
        res = super().write(value)
        self._convert_fsm_location()
        return res
