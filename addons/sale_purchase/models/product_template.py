from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    service_to_purchase = fields.Boolean(
        string="Subcontract Service",
        copy=False,
        company_dependent=True,
        help="If ticked, each time you sell this product through a SO, a RfQ is automatically created to buy the product. Tip: don't forget to set a vendor on the product.",
    )

    @api.constrains("service_to_purchase", "seller_ids", "type", "expense_policy")
    def _check_service_to_purchase(self):
        for company in self.env.user.company_ids or self.env.company:
            for template in self.with_company(company).filtered("service_to_purchase"):
                template._check_service_to_purchase_in_company(company)

    def _check_service_to_purchase_in_company(self, company):
        self.check_singleton()
        if self.type != "service":
            raise ValidationError(
                _(
                    "%(product)s is set up as a subcontracted service in %(company)s, which only a service can be.",
                    product=self.display_name,
                    company=company.display_name,
                )
            )
        if self.expense_policy != "no":
            raise ValidationError(
                _(
                    "%(product)s is re-invoiced at cost, so it is already bought through the expense and cannot also raise a RfQ in %(company)s.",
                    product=self.display_name,
                    company=company.display_name,
                )
            )
        if not self.seller_ids:
            raise ValidationError(
                _(
                    "Please define the vendor from whom you would like to purchase %(product)s automatically for %(company)s.",
                    product=self.display_name,
                    company=company.display_name,
                )
            )

    @api.onchange("type", "expense_policy")
    def _onchange_service_to_purchase(self):
        self.filtered(
            lambda p: p.type != "service" or p.expense_policy != "no"
        ).service_to_purchase = False
