from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import groupby


class ProductUom(models.Model):
    _name = "product.uom"
    _description = "Link between products and their UoMs"
    _rec_name = "barcode"
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        index=True,
        required=True,
        ondelete="cascade",
        check_company=True,
    )
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
        index=True,
        required=True,
        ondelete="cascade",
    )
    barcode = fields.Char(
        index="btree_not_null",
        copy=False,
        required=True,
    )

    _barcode_company_uniq = models.UniqueIndex(
        "(barcode, company_id) NULLS NOT DISTINCT",
        "A barcode can only be assigned to one packaging within a company.",
    )

    @api.constrains("barcode", "company_id")
    def _check_barcode_uniqueness(self):
        barcodes_by_company = {
            company: [p.barcode for p in packagings if p.barcode]
            for company, packagings in groupby(self, lambda p: p.company_id)
        }
        all_barcodes = [
            b for barcodes in barcodes_by_company.values() for b in barcodes
        ]
        if not all_barcodes:
            return
        colliding = (
            self.env["product.product"]
            .sudo()
            .search_fetch([("barcode", "in", all_barcodes)], ["barcode", "company_id"])
        )
        if not colliding:
            return
        for company, barcodes in barcodes_by_company.items():
            if not barcodes:
                continue
            wanted = set(barcodes)
            if any(
                product.barcode in wanted
                and (
                    not company
                    or not product.company_id
                    or product.company_id == company
                )
                for product in colliding
            ):
                raise ValidationError(_("A product already uses the barcode"))

    def _compute_display_name(self):
        if not self.env.context.get("show_variant_name"):
            return super()._compute_display_name()
        for record in self:
            record.display_name = (
                f"{record.barcode} for: {record.product_id.display_name}"
            )
        return None
