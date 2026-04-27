# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class DocumentUnlinkMixin(models.AbstractModel):
    """Send the related documents to trash when the record is deleted."""
    _name = 'documents.unlink.mixin'
    _description = "Documents unlink mixin"

    def unlink(self):
        """Prevent deletion of the attachments / documents and send them to the trash instead."""
        documents = self.env['documents.document'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('active', '=', True),
        ])

        for document in documents:
            document.write({
                'res_model': 'documents.document',
                'res_id': document.id,
                'active': False,
            })

        return super().unlink()
