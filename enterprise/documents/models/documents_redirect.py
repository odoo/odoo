from odoo import api, fields, models


class DocumentRedirect(models.Model):
    """Model used to keep the old links valid after the 18.0 migration.

    Do *NOT* use that model or inherit from it, it will be removed in the future.
    """

    _name = "documents.redirect"
    _description = "Document Redirect"
    _log_access = False

    access_token = fields.Char(required=True, index="btree")
    document_id = fields.Many2one("documents.document", ondelete="cascade")

    @api.model
    def _get_redirection(self, access_token):
        """Redirect to the right document, only if its access is view.

        We won't redirect if the access is not "view" to not give write access
        if the permission has been changed on the document (or to not give the
        token if the access is "none").
        """
        return self.search(
            # do not give write access for old token
            [("access_token", "=", access_token), ('document_id.access_via_link', '=', 'view')],
            limit=1,
        ).document_id
