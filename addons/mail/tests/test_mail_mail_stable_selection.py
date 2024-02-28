

from odoo.tests.common import TransactionCase

class TestMailMailStableSelection(TransactionCase):
    """Only relevant in stable as a hotfix. May be removed in master."""

    def test_mail_mail_stable_selection(self):
        # remove all selections
        message_type_selections = self.env['ir.model.fields']._get('mail.message', 'message_type').selection_ids
        message_type_selections.filtered(lambda s: s.value == 'auto_comment').unlink()
        self.env['mail.mail']._fields_get_message_type_update_selection(self.env['mail.message']._fields['message_type'].selection)
        # force convert to cache with specific language so it has to fetch related from DB
        mail = self.env['mail.mail'].create({'subject': 'test', 'message_type': 'auto_comment'})
        mail.invalidate_recordset(['message_type'])
        self.assertEqual(mail.with_context(lang="en_US").message_type, 'auto_comment')
