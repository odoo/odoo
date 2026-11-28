from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_tr_ctsp_number = fields.Char(
        string="CTSP Number",
        compute="_compute_l10n_tr_ctsp_number",
        inverse="_set_l10n_tr_ctsp_number",
        help="A helper field that syncs the CTSP Number with the product's variants. \n"
        "- If you set a value here, it will be applied to all variants. \n"
        "- If variants have different values, this field will be blank. \n"
        "This is a Turkish localization code for products.",
    )
    l10n_tr_customer_line_code = fields.Char(
        string="Customer Line Code",
        compute='_compute_l10n_tr_customer_line_code',
        inverse='_set_l10n_tr_customer_line_code',
        help="Within the scope of the IPAC, it refers to the reference line "
             "number of the exported product item on the document.",
    )
    l10n_tr_seller_line_code = fields.Char(
        string="Seller Line Code",
        compute='_compute_l10n_tr_seller_line_code',
        inverse='_set_l10n_tr_seller_line_code',
        help="Within the scope of the IPAC, it refers to the reference line "
             "number of the input (purchase/import) item on the document.",
    )

    @api.depends("product_variant_ids.l10n_tr_ctsp_number")
    def _compute_l10n_tr_ctsp_number(self):
        self._compute_template_field_from_variant_field("l10n_tr_ctsp_number")

    def _set_l10n_tr_ctsp_number(self):
        self._set_product_variant_field("l10n_tr_ctsp_number")

    @api.depends("product_variant_ids.l10n_tr_customer_line_code")
    def _compute_l10n_tr_customer_line_code(self):
        self._compute_template_field_from_variant_field("l10n_tr_customer_line_code")

    def _set_l10n_tr_customer_line_code(self):
        self._set_product_variant_field("l10n_tr_customer_line_code")

    @api.depends("product_variant_ids.l10n_tr_seller_line_code")
    def _compute_l10n_tr_seller_line_code(self):
        self._compute_template_field_from_variant_field("l10n_tr_seller_line_code")

    def _set_l10n_tr_seller_line_code(self):
        self._set_product_variant_field("l10n_tr_seller_line_code")
