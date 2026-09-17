"""A `document.document` in the trash is still a row, and two call sites forgot.

Both defects below come from reaching for linked documents through a default
`search`, which `active_test` scopes to the active ones. A trashed document
still holds `attachment_id` and still carries `res_model`/`res_id`, so the
half that is invisible to the search is exactly the half that costs something:
once as a lost file, once as a constraint violation.

The mixin (`mixin.documents`) is community, but `product.template` is the only
concrete host a bundled module declares, so its behaviour is pinned here.
"""

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestTrashedLinkedDocuments(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.folder = cls.env["document.document"].create(
            {"name": "trash integrity", "type": "folder"}
        )
        cls.company = cls.env["res.company"].create(
            {"name": "trash integrity co", "product_folder_id": cls.folder.id}
        )

    def _product(self, name):
        return self.env["product.template"].create(
            {"name": name, "company_id": self.company.id}
        )

    def _attach(self, product):
        return self.env["ir.attachment"].create(
            {
                "name": "datasheet.txt",
                "raw": b"datasheet",
                "res_model": "product.template",
                "res_id": product.id,
            }
        )

    def _document_of(self, attachment):
        return (
            self.env["document.document"]
            .with_context(active_test=False)
            .search([("attachment_id", "=", attachment.id)])
        )

    def test_a_trashed_document_survives_the_record_it_was_linked_to(self):
        """The trash is a delay before deletion, not another way of deleting now.

        Deleting the product detaches the ACTIVE document and sends it to the
        trash, which is recoverable for `document.deletion_delay` days. The
        already-trashed one was skipped by that detach, so its attachment still
        pointed at the product; deleting the product took the attachment, and
        `attachment_id`'s `ondelete="cascade"` took the document with it --
        permanently, and well before the date its own archive message promised.
        """
        product = self._product("trashed source")
        attachment = self._attach(product)
        document = self._document_of(attachment)
        self.assertTrue(document, "the bridge must have produced a document")

        document.action_archive()
        self.env.flush_all()
        self.assertFalse(document.active)

        product.unlink()
        self.env.flush_all()

        self.assertTrue(
            document.exists(),
            "a document in the trash must outlive the record it was linked to, "
            "exactly as an active one does",
        )
        self.assertTrue(
            document.attachment_id.exists(), "and keep the file it is a document of"
        )
        self.assertFalse(document.res_model, "detached from the record that is gone")
        self.assertFalse(document.res_id)
        self.assertFalse(document.active, "and it stays in the trash, not restored")

    def test_an_active_document_survives_it_too(self):
        """The control this is being aligned with, so a regression names itself."""
        product = self._product("active source")
        attachment = self._attach(product)
        document = self._document_of(attachment)

        product.unlink()
        self.env.flush_all()

        self.assertTrue(document.exists())
        self.assertFalse(document.res_model)
        self.assertFalse(
            document.active, "deleting the source sends the document to the trash"
        )

    def test_relinking_an_attachment_a_trashed_document_holds_makes_no_second_one(self):
        """`unique (attachment_id)` is a hard constraint: the guard must see every row.

        The "is this attachment already documented?" check ran a default
        search, so a trashed document did not count; `create` then inserted a
        second row for the same attachment and the transaction died on
        `document_document_attachment_unique` -- a raw UniqueViolation rather
        than a UserError, so no caller could recover from it.
        """
        source = self._product("first host")
        attachment = self._attach(source)
        document = self._document_of(attachment)
        document.action_archive()
        self.env.flush_all()

        destination = self._product("second host")
        attachment.write({"res_id": destination.id})
        self.env.flush_all()

        self.assertEqual(
            self._document_of(attachment),
            document,
            "the attachment must still be held by exactly the one document that "
            "already held it",
        )

    def test_the_guard_still_lets_a_first_document_be_created(self):
        """Negative control: a guard that refused everything would pass the above."""
        product = self._product("fresh host")
        attachment = self._attach(product)

        self.assertTrue(
            self._document_of(attachment),
            "an attachment nobody documents yet must still get its document, or "
            "the test above proves only that creation is broken",
        )
