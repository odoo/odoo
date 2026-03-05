# Copyright 2019 Creu Blanca
# Copyright 2025 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import html_escape


class DocumentPage(models.Model):
    _inherit = "document.page"
    _description = "Document Page"

    reference = fields.Char(
        help="Used to find the document, it can contain letters, numbers and _"
    )
    content_parsed = fields.Html(
        "Parsed Content", compute="_compute_content_parsed", sanitize=False, store=True
    )

    def get_formview_action(self, access_uid=None):
        res = super().get_formview_action(access_uid)
        view_id = self.env.ref("document_page.view_wiki_form").id
        res["views"] = [(view_id, "form")]
        return res

    @api.depends("content")
    def _compute_content_parsed(self):
        for record in self:
            record.content_parsed = record.get_content()

    @api.constrains("reference")
    def _check_reference_validity(self):
        for rec in self:
            if not rec.reference:
                continue
            regex = r"^[a-zA-Z_][a-zA-Z0-9_]*$"
            if not re.match(regex, rec.reference):
                raise ValidationError(self.env._("Reference is not valid"))
            domain = [("reference", "=", rec.reference), ("id", "!=", rec.id)]
            if self.search(domain):
                raise ValidationError(self.env._("Reference must be unique"))

    def _get_document(self, code):
        return self.search([("reference", "=", code)], limit=1)

    def get_content(self):
        self.ensure_one()
        content_parsed = raw = self.content or ""
        for text in re.findall(r"\{\{.*?\}\}", raw):
            reference = text.replace("{{", "").replace("}}", "")
            content_parsed = content_parsed.replace(
                text, self._resolve_reference(reference)
            )
        return content_parsed

    def _resolve_reference(self, code):
        doc = self._get_document(code)
        if self.env.context.get("raw_reference", False):
            return html_escape(doc.display_name if doc else code)
        sanitized_code = html_escape(code)
        oe_model = doc._name if doc else self._name
        oe_id = doc.id if doc else ""
        name = html_escape(doc.display_name) if doc else sanitized_code
        return (
            f"<a href='#' class='oe_direct_line' data-oe-model='{oe_model}' "
            f"data-oe-id='{oe_id}' name='{sanitized_code}'>"
            f"{name}</a>"
        )

    def get_raw_content(self):
        return Markup(self.with_context(raw_reference=True).get_content())

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("reference") and vals.get("name"):
                reference = self.env["ir.http"]._slugify(vals["name"]).replace("-", "_")
                vals["reference"] = reference
        return super().create(vals_list)
