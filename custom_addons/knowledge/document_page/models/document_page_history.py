# Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models

from odoo.addons.html_editor.models.diff_utils import (
    generate_comparison,
)


class DocumentPageHistory(models.Model):
    """This model is necessary to manage a document history."""

    _name = "document.page.history"
    _description = "Document Page History"
    _order = "id DESC"

    page_id = fields.Many2one("document.page", "Page", ondelete="cascade")
    name = fields.Char(index=True)
    summary = fields.Char(index=True)
    content = fields.Html(sanitize=False)
    diff = fields.Html(compute="_compute_diff", sanitize_tags=False)

    company_id = fields.Many2one(
        "res.company",
        "Company",
        help="If set, page is accessible only from this company",
        related="page_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )

    def _compute_diff(self):
        """Shows a diff between this version and the previous version"""
        history = self.env["document.page.history"]
        for rec in self:
            prev = history.search(
                [
                    ("page_id", "=", rec.page_id.id),
                    ("create_date", "<", rec.create_date),
                ],
                limit=1,
                order="create_date DESC",
            )
            rec.diff = self._get_diff(prev.id, rec.id)

    def _get_diff(self, v1, v2):
        text1 = v1 and self.browse(v1).content or ""
        text2 = v2 and self.browse(v2).content or ""
        return generate_comparison(text1, text2)

    @api.depends("page_id")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.id, "%s #%i" % (rec.page_id.name, rec.id)
