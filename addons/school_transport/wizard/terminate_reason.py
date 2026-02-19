# See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models


class TerminateReasonTransport(models.TransientModel):
    _inherit = "terminate.reason"

    transport_info = fields.Text(help="Enter transport information")

    @api.model
    def default_get(self, fields):
        res = super(TerminateReasonTransport, self).default_get(fields)
        student_rec = self.env["student.student"].browse(self._context.get("active_id"))
        student_transport_rec = self.env["transport.registration"].search(
            [
                ("student_id", "=", student_rec.id),
                ("state", "in", ["confirm", "pending", "paid"]),
            ]
        )
        transport_msg = ""
        for rec in student_transport_rec:
            transport_msg += (
                "\nStudent is registered for the root"
                + " "
                + rec.name.name
                + " "
                + "the vehicle number is"
                + " "
                + rec.vehicle_id.license_plate
            )
        res.update({"transport_info": transport_msg})
        return res
