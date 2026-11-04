# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo.tests import common


class TestFleetSendMail(common.TransactionCase):

    def test_send_mail_with_attachments(self):
        """
            Attachments added in the "Mail to Driver" wizard should be sent with the message
        """
        driver = self.env["res.partner"].create({
            "name": "Test Driver",
            "email": "test.driver@example.com",
        })
        brand = self.env["fleet.vehicle.model.brand"].create({
            "name": "Audi",
        })
        model = self.env["fleet.vehicle.model"].create({
            "brand_id": brand.id,
            "name": "A3",
        })
        car = self.env["fleet.vehicle"].create({
            "model_id": model.id,
            "driver_id": driver.id,
        })
        attachment = self.env["ir.attachment"].create({
            "name": "test.txt",
            "datas": base64.b64encode(b"Test attachment"),
        })

        wizard = self.env["fleet.vehicle.send.mail"].create({
            "vehicle_ids": car.ids,
            "subject": "Test subject",
            "body": "<p>Test body</p>",
            "attachment_ids": attachment.ids,
        })
        wizard.action_send()

        message = car.message_ids.filtered(lambda m: m.subject == "Test subject")
        self.assertEqual(len(message), 1)
        self.assertEqual(len(message.attachment_ids), 1)
        self.assertRecordValues(message.attachment_ids, [{
            "name": "test.txt",
            "raw": b"Test attachment",
            "res_model": "fleet.vehicle",
            "res_id": car.id,
        }])
