from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import clean_context

_debug = DebugLog(__name__)


class DocumentsDocument(models.Model):
    _inherit = "document.document"

    product_template_id = fields.Many2one(
        comodel_name="product.template",
        string="Product",
        compute="_compute_product",
        search="_search_product_template_id",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product Variant",
        compute="_compute_product",
        search="_search_product_id",
    )

    @api.depends("res_id", "res_model")
    def _compute_product(self):
        ProductTemplate = self.env["product.template"]
        Product = self.env["product.product"]
        for document in self:
            document.product_template_id = (
                document.res_model == "product.template"
                and ProductTemplate.browse(document.res_id)
            )
            document.product_id = (
                document.res_model == "product.product"
                and Product.browse(document.res_id)
            )

    @api.model
    def _search_product_template_id(self, operator, value):
        return self._search_related_product_field(
            operator, value, "product_template_id"
        )

    @api.model
    def _search_product_id(self, operator, value):
        return self._search_related_product_field(operator, value, "product_id")

    @api.model
    def _search_related_product_field(self, operator, value, field_name) -> Domain:
        assert field_name in ("product_template_id", "product_id")
        Model = self.env[self._fields[field_name].comodel_name]
        if operator == "in":
            # `True` and `False` are sentinels for "any" and "no" related product.
            # Test them by identity, never by equality or membership: Python has
            # `True == 1` and `False == 0` with equal hashes, so `True in value`
            # also fires on the real product id 1 and `value - {True}` then drops
            # that id, widening the search to every product-linked document.
            if any(v is True for v in value):
                _debug.logic("product_search", by="any_product", field=field_name)
                return Domain(field_name, "not in", [False]) | Domain(
                    field_name, "in", [v for v in value if v is not True]
                )
            if any(v is False for v in value):
                _debug.logic("product_search", by="no_product", field=field_name)
                return Domain(
                    "res_model", "!=", Model._name
                ) | self._search_related_product_field(
                    operator, [v for v in value if v is not False], field_name
                )
            query_model = Model._search(
                Domain.OR(
                    Domain(Model._rec_name if isinstance(v, str) else "id", operator, v)
                    for v in value
                    if v
                )
            )
        elif operator == "any" and isinstance(value, Domain):
            _debug.logic("product_search", by="subdomain", field=field_name)
            query_model = Model._search(value)
        elif operator.endswith("like") and not operator.startswith("not"):
            _debug.logic("product_search", by="name", field=field_name)
            query_model = Model._search([(Model._rec_name, operator, value)])
        else:
            _debug.logic("product_search_unsupported", operator=operator)
            return NotImplemented
        return (
            Domain.FALSE
            if query_model.is_empty()
            else Domain("res_id", "in", query_model)
        ) & Domain("res_model", "=", Model._name)

    def create_product_template(self):
        # Creates a single product.template for the whole recordset and links every
        # document to it; the product image is taken from the first image document.
        if not self:
            _debug.logic("product_create_refused", reason="no_documents")
            raise UserError(
                self.env._("Select at least one document to create a product from.")
            )
        # clean_context: the caller is the Documents client, whose context carries
        # its own `default_*` keys. They must not reach product.template.create -
        # `default_type='folder'` is a valid document.document type but not a
        # valid product one, and `default_active=False` would create the product
        # archived and invisible.
        product = (
            self.env["product.template"]
            .with_context(clean_context(self.env.context))
            .create({"name": self.env._("Product created from Documents")})
        )

        _debug.lifecycle(
            "product_created_from_documents", documents=self, product=product
        )
        for document in self:
            if document.res_model or document.res_id:
                att_copy = document.attachment_id.with_context(no_document=True).copy()
                document = document.copy({"attachment_id": att_copy.id})
            document.write(
                {
                    "res_model": product._name,
                    "res_id": product.id,
                }
            )
            is_image = (document.mimetype or "").partition("/")[0] == "image"
            if is_image and not product.image_1920:
                _debug.logic("product_image_taken", document=document)
                product.write({"image_1920": document.datas})

        view_id = product.get_formview_id()
        return {
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "name": self.env._("New product template"),
            "context": clean_context(self.env.context),
            "view_mode": "form",
            "views": [(view_id, "form")],
            "res_id": product.id,
            "view_id": view_id,
        }

    def _get_details_panel_res_models(self) -> list[str]:
        return [*super()._get_details_panel_res_models(), "product.product"]
