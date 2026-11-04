from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UniversitySubject(models.Model):
    _inherit = "university.subject"

    book_product_id = fields.Many2one(
        "product.product",
        string="Required Book",
        domain="[('purchase_ok', '=', True)]",
        help="Exactly one purchasable book product required for this subject.",
        index=True,
        ondelete="restrict",
    )

    @api.constrains("book_product_id")
    def _check_book_product_purchasable(self):
        for subject in self:
            product = subject.book_product_id
            if product and not product.purchase_ok:
                raise ValidationError(
                    _("Book product '%(product)s' on subject '%(subject)s' must be purchasable.")
                    % {
                        "product": product.display_name,
                        "subject": subject.display_name,
                    }
                )
