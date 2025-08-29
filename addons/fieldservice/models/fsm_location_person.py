# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FSMLocationPerson(models.Model):
    _name = "fsm.location.person"
    _description = "Field Service Location Person Info"
    _rec_name = "location_id"
    _order = "sequence"

    location_id = fields.Many2one(
        "fsm.location", string="Location", required=True, index=True
    )
    person_id = fields.Many2one(
        "fsm.person", string="Worker", required=True, index=True
    )
    sequence = fields.Integer(required=True, default="10")
    phone = fields.Char(related="person_id.phone")
    email = fields.Char(related="person_id.email")
    owner_id = fields.Many2one(related="location_id.owner_id", string="Owner")
    contact_id = fields.Many2one(related="location_id.contact_id", string="Contact")

    _sql_constraints = [
        (
            "location_person_uniq",
            "unique(location_id,person_id)",
            "The worker is already linked to this location.",
        )
    ]
