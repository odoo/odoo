from odoo.tests import TransactionCase, tagged

from odoo.addons.web.models.models import PENDING_ATTACHMENTS_KEY, PENDING_ATTACHMENT_FIELDS_KEY


@tagged('post_install', '-at_install')
class TestWebSavePendingAttachments(TransactionCase):

    def test_pending_attachment_in_inherited_field_linked_to_parent(self):
        """If the field on the model that the attachment is for is related,
        the attachment should be linked to it instead."""
        user = self.env['res.users'].create({
            'name': 'Test user',
            'login': 'test_pending_attachment_user',
        })
        attachment = self.env['ir.attachment'].create({
            'name': 'pending.png',
            'raw': b'fake',
            'res_model': 'res.users',
        })
        user.with_context(**{
            PENDING_ATTACHMENTS_KEY: attachment.ids,
            PENDING_ATTACHMENT_FIELDS_KEY: {'comment': attachment.ids},
        }).web_save({'comment': '<p>Notes</p>'}, {})
        self.assertEqual(attachment.res_model, 'res.partner')
        self.assertEqual(attachment.res_id, user.partner_id.id)
