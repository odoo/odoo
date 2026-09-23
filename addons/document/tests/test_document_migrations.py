from odoo.modules.module import get_module_path, load_script
from odoo.tests import tagged

from .test_document_common import TransactionCaseDocuments


@tagged("post_install", "-at_install")
class TestFileExtensionMigration(TransactionCaseDocuments):
    def _migrate(self):
        script = load_script(
            f"{get_module_path('document')}/migrations/1.20/post-migrate.py",
            "document_1_20_post_migrate",
        )
        self.env.flush_all()
        script.migrate(self.env.cr, "1.19")

    def _document(self, name, stored_extension):
        document = self.env["document.document"].create(
            {"name": name, "raw": b"x", "folder_id": self.folder_a.id}
        )
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE document_document SET file_extension = %s WHERE id = %s",
            [stored_extension, document.id],
        )
        document.invalidate_recordset(["file_extension"])
        return document

    def test_a_derived_short_extension_becomes_the_file_s_own(self):
        markdown = self._document("notes.markdown", "md")
        archive = self._document("page.mhtml", "eml")
        self._migrate()
        self.assertEqual(markdown.file_extension, "markdown")
        self.assertEqual(archive.file_extension, "mhtml")

    def test_a_real_short_extension_and_an_operator_s_choice_are_kept(self):
        plain = self._document("README.md", "md")
        chosen = self._document("manual.markdown", "txt")
        self._migrate()
        self.assertEqual(plain.file_extension, "md")
        self.assertEqual(chosen.file_extension, "txt")

    def test_a_fresh_install_does_nothing(self):
        markdown = self._document("notes.markdown", "md")
        script = load_script(
            f"{get_module_path('document')}/migrations/1.20/post-migrate.py",
            "document_1_20_post_migrate_fresh",
        )
        script.migrate(self.env.cr, None)
        markdown.invalidate_recordset(["file_extension"])
        self.assertEqual(markdown.file_extension, "md")
