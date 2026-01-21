from odoo import _, api, fields, models

from odoo.exceptions import ValidationError
from odoo.fields import Domain


class ProductProduct(models.Model):
    _inherit = "product.product"

    l10n_tr_ctsp_number = fields.Char(
        string="CTSP Number",
        copy=False,
        index="btree_not_null",
        help="This code is a unique identifier for the product in "
        "Turkey's Centralized Trade and Stock Management System (CTSP).",
    )
    l10n_tr_seller_line_code = fields.Char(
        string="Seller Line Code",
        copy=False,
        help="Within the scope of the IPAC, it refers to the reference line "
             "number of the input (purchase/import) item on the document.",
    )
    l10n_tr_customer_line_code = fields.Char(
        string="Customer Line Code",
        size=11,
        copy=False,
        help="Within the scope of the IPAC, it refers to the reference line "
        "number of the exported product item on the document.",
    )

    @api.constrains("l10n_tr_ctsp_number")
    def _check_l10n_tr_ctsp_number(self):
        for record in self:
            if record.l10n_tr_ctsp_number and len(record.l10n_tr_ctsp_number) > 12:
                raise ValidationError(_("CTSP Number must be 12 digits or fewer."))

    def _get_product_domain_search_order(self, **vals):
        # Extend _get_product_domain_search_order
        # UBL TR requires searching with CTSP Number too

        sorted_domains = super()._get_product_domain_search_order(**vals)
        if self.env.context.get("parse_for_ubl_tr"):
            if ctsp_number := vals.get("ctsp_number"):
                sorted_domains.append((13, Domain("l10n_tr_ctsp_number", "=", ctsp_number)))
        return sorted_domains
