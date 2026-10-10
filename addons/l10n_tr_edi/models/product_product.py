from odoo import _, api, fields, models

from odoo.exceptions import ValidationError


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
