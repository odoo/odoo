# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged("-at_install", "post_install")
class TestHtmlFieldPendingAttachments(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.view = cls.env["ir.ui.view"].create({
            "name": "html_editor.converter.test.pending.form",
            "model": "html_editor.converter.test",
            "type": "form",
            "arch": """
                <form>
                    <sheet>
                        <field name="char"/>
                        <field name="html" widget="html"/>
                    </sheet>
                </form>
            """,
        })
        cls.action = cls.env["ir.actions.act_window"].create({
            "name": "Pending attachments test",
            "res_model": "html_editor.converter.test",
            "view_mode": "form",
            "view_id": cls.view.id,
        })

    @property
    def _new_record_url(self):
        return f"/odoo/action-{self.action.id}/new"

    def test_pending_attachment_shown_in_same_record_dialog(self):
        self.start_tour(
            self._new_record_url,
            "html_field_pending_attachments_same_record_tour",
            login="admin",
        )

        record = self.env["html_editor.converter.test"].search(
            [], order="id desc", limit=1,
        )
        self.assertTrue(record, "the tour should have created a record")
        attachment = self.env["ir.attachment"].search([
            ("name", "=", "pending.png"),
            ("res_model", "=", "html_editor.converter.test"),
            ("res_id", "=", record.id),
        ])
        self.assertEqual(
            len(attachment), 1,
            "the pasted attachment should be linked to the saved record",
        )

    def test_pending_attachment_not_shown_in_other_new_record_dialog(self):
        self.start_tour(
            self._new_record_url,
            "html_field_pending_attachments_other_record_tour",
            login="admin",
        )

    def test_pending_attachment_unlinked_on_discard(self):
        self.start_tour(
            self._new_record_url,
            "html_field_pending_attachments_discard_tour",
            login="admin",
        )

        orphan_attachments = self.env["ir.attachment"].search([
            ("name", "=", "pending.png"),
            ("res_model", "=", "html_editor.converter.test"),
            ("res_id", "=", 0),
        ])
        self.assertFalse(
            orphan_attachments,
            "discarding the record should unlink the pending attachment created during commit",
        )
        self.assertFalse(
            self.env["html_editor.converter.test"].search([]),
            "discarding the record should not create a record",
        )
