import base64

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged, users


@tagged("ir_attachment")
class TestAttachment(MailCommon):

    @users("employee")
    def test_register_as_main_attachment(self):
        """ Test 'register_as_main_attachment', especially the multi support """
        records_model1 = self.env["mail.test.simple.main.attachment"].create([
            {
                "name": f"First model {idx}",
            }
            for idx in range(5)
        ])
        records_model2 = self.env["mail.test.gateway.main.attachment"].create([
            {
                "name": f"Second model {idx}",
            }
            for idx in range(5)
        ])
        record_nomain = self.env["mail.test.simple"].create({"name": "No Main Attachment"})
        attachments = self.env["ir.attachment"].create([
            {
                "datas": base64.b64encode(b'AttContent'),
                "name": f"AttachName_{record.name}.pdf",
                "mimetype": "application/pdf",
                "res_id": record.id,
                "res_model": record._name,
            }
            for record in records_model1
        ] + [
            {
                "datas": base64.b64encode(b'AttContent'),
                "name": f"AttachName_{record.name}.pdf",
                "mimetype": "application/pdf",
                "res_id": record.id,
                "res_model": record._name,
            }
            for record in records_model2
        ] + [
            {
                "datas": base64.b64encode(b'AttContent'),
                "name": "AttachName_free.pdf",
                "mimetype": "application/pdf",
            }, {
                "datas": base64.b64encode(b'AttContent'),
                "name": f"AttachName_{record_nomain.name}.pdf",
                "mimetype": "application/pdf",
                "res_id": record_nomain.id,
                "res_model": record_nomain._name,
            }
        ])
        attachments.register_as_main_attachment()
        for record, attachment in zip(records_model1, attachments[:5]):
            self.assertEqual(record.message_main_attachment_id, attachment)
        for record, attachment in zip(records_model2, attachments[5:10]):
            self.assertEqual(record.message_main_attachment_id, attachment)
