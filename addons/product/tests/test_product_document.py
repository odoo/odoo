# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.base.models import ir_attachment
from odoo.tests import tagged, TransactionCase


@tagged("post_install", "-at_install")
class TestProductDocument(TransactionCase):
    def test_fetch_product_document_field_does_not_scan_all_attachments(self):
        """Reading a field on a small set of product.document records should not
        require scanning every ir.attachment in the database to compute access.
        """
        user = self.env["res.users"].create({
            "name": "Test Product Doc User",
            "login": "test_product_doc_user",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })

        partner = self.env["res.partner"].create({"name": "Noise target"})
        # Unrelated attachments that would blow up a naive "scan everything" fallback
        self.env["ir.attachment"].create([{
            "name": f"Noise Document {i}",
            "res_model": "res.partner",
            "res_id": partner.id,
            "type": "binary",
        } for i in range(10)])

        template = self.env["product.template"].create({"name": "Test Product"})
        document = self.env["product.document"].create({
            "name": "doc.pdf",
            "res_model": "product.template",
            "res_id": template.id,
            "type": "binary",
        })

        with patch.object(ir_attachment, "MAX_SEARCH_LIMIT", 5):
            documents = self.env["product.document"].browse(document.id).with_user(user)
            documents.invalidate_recordset()
            # This used to raise ValueError("Cannot search, too many attachments")
            # because computing access for `documents` (a small, known set of ids)
            # fell back to scanning every ir.attachment with a res_model set.
            self.assertEqual(documents.name, "doc.pdf")
