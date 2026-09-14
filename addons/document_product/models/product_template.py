from odoo import _, api, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "mixin.documents.product"]

    @api.depends("product_variant_ids")
    def _compute_product_document_count(self):
        template_counts = {}
        variant_counts = {}
        if self:
            tmpl_data = self.env["document.document"]._read_group(
                [("res_model", "=", "product.template"), ("res_id", "in", self.ids)],
                ["res_id"],
                ["__count"],
            )
            template_counts = dict(tmpl_data)
            variant_ids = self.product_variant_ids
            if variant_ids:
                var_data = self.env["document.document"]._read_group(
                    [
                        ("res_model", "=", "product.product"),
                        ("res_id", "in", variant_ids.ids),
                    ],
                    ["res_id"],
                    ["__count"],
                )
                variant_counts = dict(var_data)
        _debug.perf.count(
            "template_document_counts",
            templates=self,
            tmpl_rows=len(template_counts),
            variant_rows=len(variant_counts),
        )
        for template in self:
            count = template_counts.get(template.id, 0)
            for variant in template.product_variant_ids:
                count += variant_counts.get(variant.id, 0)
            template.product_document_count = count

    def _get_domain_product_document(self):
        self.check_singleton()
        return (
            Domain("res_model", "=", "product.template")
            & Domain("res_id", "in", self.ids)
        ) | (
            Domain("res_model", "=", "product.product")
            & Domain("res_id", "in", self.product_variant_ids.ids)
        )

    @api.readonly
    def action_view_documents(self):
        self.check_singleton()
        return {
            "name": _("Documents"),
            "type": "ir.actions.act_window",
            "res_model": "document.document",
            "view_mode": "kanban,list,form",
            "views": [
                (
                    self.env.ref(
                        "document_product.view_documents_document_product_kanban"
                    ).id,
                    "kanban",
                ),
                (
                    self.env.ref(
                        "document_product.view_documents_document_product_list"
                    ).id,
                    "list",
                ),
                (
                    self.env.ref(
                        "document_product.view_documents_document_product_form"
                    ).id,
                    "form",
                ),
            ],
            "search_view_id": self.env.ref(
                "document_product.view_documents_document_product_search"
            ).id,
            "context": {
                "default_res_model": self._name,
                "default_res_id": self.id,
                "default_company_id": self.company_id.id,
            },
            "domain": self._get_domain_product_document(),
            "target": "current",
            "help": """
                <p class="o_view_nocontent_smiling_face">
                    %s
                </p>
                <p>
                    %s
                    <br/>
                    %s
                </p>
                <p>
                    <a class="oe_link" href="https://www.odoo.com/documentation/latest/_downloads/eaa2883bd361273b475c9765f64e3e0c/pdfquotebuilderexamples.zip">
                    %s
                    </a>
                </p>
            """
            % (
                _("Upload files to your product"),
                _(
                    "Use this feature to store any files you would like to share with your customers"
                ),
                _("(e.g: product description, ebook, legal notice, ...)."),
                _("Download examples"),
            ),
        }
