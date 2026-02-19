# See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class TransferVehicle(models.TransientModel):
    _name = "transfer.vehicle"
    _description = "transfer vehicle"

    name = fields.Many2one("student.student", "Student Name", readonly=True)
    participation_id = fields.Many2one(
        "transport.participant", "Participation", required=True
    )
    root_id = fields.Many2one("student.transport", "Root", required=True)
    old_vehicle_id = fields.Many2one("fleet.vehicle", "Old Vehicle No", required=True)
    new_vehicle_id = fields.Many2one("fleet.vehicle", "New Vehicle No", required=True)

    @api.model
    def default_get(self, fields):
        """Override method to get student."""
        active_id = self._context.get("active_id")
        result = super(TransferVehicle, self).default_get(fields)
        if active_id:
            student = self.env["student.student"].browse(active_id)
            if "name" in fields:
                result.update({"name": student.id})
        return result

    @api.onchange("participation_id")
    def onchange_participation_id(self):
        """Method to get transport id and vehicle of participant."""
        for rec in self:
            if rec.participation_id:
                rec.root_id = rec.participation_id.transport_id.id
                rec.old_vehicle_id = rec.participation_id.vehicle_id.id

    def vehicle_transfer(self):
        """Method to transfer vehicle."""
        for rec in self:
            vehi_data = rec.old_vehicle_id
            vehi_new_data = rec.new_vehicle_id
            # check for transfer in same vehicle
            if vehi_data.id == vehi_new_data.id:
                raise UserError(
                    _("Error ! Sorry you can not transfer in same vehicle.")
                )
            # First Check Is there vacancy or not
            person = int(vehi_data.participant) + 1
            if vehi_data.capacity < person:
                raise UserError(_("Error ! There is No More vacancy on this vehicle."))
            # remove entry of participant in old vehicle.
            participants = [prt_id.id for prt_id in vehi_data.vehi_participants_ids]
            if rec.participation_id.id in participants:
                participants.remove(rec.participation_id.id)
            vehi_data.write({"vehi_participants_ids": [(6, 0, participants)]})
            # entry of participant in new vehicle.
            participants = [prt_id.id for prt_id in vehi_new_data.vehi_participants_ids]
            participants.append(rec.participation_id.id)
            vehi_new_data.write({"vehi_participants_ids": [(6, 0, participants)]})
            rec.participation_id.write({"vehicle_id": rec.new_vehicle_id.id})
