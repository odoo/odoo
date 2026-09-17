"""A `res_model` naming a model the registry no longer has is a dangling link.

Uninstalling a module does not clean the `res_model` strings its records left
on `document.document` rows, so a document can outlive the model it points at.
Three sites read that as "not linked" -- `_compute_res_name`,
`_compute_res_model_name` and `_inverse_res_record` all check
`res_model in self.env` -- and two write paths did not. They are the ones that
hurt, because the value is not read but USED: one indexed `self.env[res_model]`
and raised a bare `KeyError`, the other stamped the dead name onto an
attachment it had just created.
"""

from odoo.tests.common import TransactionCase, tagged

GONE = "gone.module.model"


@tagged("post_install", "-at_install")
class TestDanglingResModel(TransactionCase):
    def _orphaned(self, name, with_content=True):
        """A document pointing at a model the registry does not have.

        Written through SQL because there is no supported way to reach this
        state forwards -- it is what an uninstall leaves behind.
        """
        vals = {"name": name, "type": "binary"}
        if with_content:
            vals["raw"] = b"before"
        document = self.env["document.document"].create(vals)
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE document_document SET res_model = %s, res_id = %s WHERE id = %s",
            (GONE, 42, document.id),
        )
        self.env.invalidate_all()
        self.assertNotIn(document.res_model, self.env)
        return document

    def test_reading_a_dangling_link_answers_rather_than_raises(self):
        """The three sites that already got this right, pinned."""
        document = self._orphaned("orphan-read.txt")

        self.assertFalse(document.res_name)
        self.assertFalse(document.res_model_name)

    def test_filling_an_empty_orphaned_document_clears_the_link(self):
        """The `KeyError` path: an upload request against an uninstalled model.

        `_write_attach_empty_document` already cleared the link when the linked
        RECORD was gone; a model that is gone is the strongest form of that, and
        it used to index `self.env[res_model]` before testing for it -- raising
        `KeyError: '<model>'`, which reaches the client as a 500 rather than as
        anything a caller could handle.
        """
        document = self._orphaned("orphan-empty.txt", with_content=False)

        document.write({"raw": b"uploaded at last"})

        self.assertFalse(document.res_model, "the dangling link is dropped")
        self.assertFalse(document.res_id)
        self.assertTrue(document.attachment_id)
        self.assertEqual(
            (document.attachment_id.res_model, document.attachment_id.res_id),
            ("document.document", document.id),
            "and the new file belongs to the document itself",
        )

    def test_a_new_attachment_never_inherits_a_dead_model(self):
        """`ir.attachment` denies access to anything it cannot access-check, so
        stamping a dead `res_model` onto a fresh attachment makes that
        attachment unreadable -- the document poisons its own new version."""
        document = self._orphaned("orphan-swap.txt", with_content=False)
        document.write({"raw": b"first"})
        replacement = self.env["ir.attachment"].create(
            {"name": "replacement.txt", "raw": b"second"}
        )

        document.write({"attachment_id": replacement.id})

        self.assertNotEqual(
            replacement.res_model, GONE, "the dead model must not be propagated"
        )
        self.assertEqual(
            replacement.raw,
            b"second",
            "and the replacement stays readable -- `ir.attachment` denies "
            "access to a row whose res_model it cannot access-check, so "
            "stamping a dead name on it makes the new version unreadable",
        )
        self.assertEqual(document.attachment_id, replacement)

    def test_a_live_link_is_left_alone(self):
        """Negative control: the guard must not unlink a document that is fine."""
        partner = self.env["res.partner"].create({"name": "still here"})
        document = self.env["document.document"].create(
            {"name": "linked.txt", "type": "binary"}
        )
        document.write({"res_model": "res.partner", "res_id": partner.id})

        document.write({"raw": b"content"})

        self.assertEqual(document.res_model, "res.partner")
        self.assertEqual(document.res_id, partner.id)
