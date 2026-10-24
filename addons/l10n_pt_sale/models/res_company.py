from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_pt_down_payment_product_id = fields.Many2one(
        comodel_name='product.product',
        string="Down Payment Product (PT)",
        help="Product of the down payment lines of Portuguese invoices: the SAF-T (PT) needs a product on every line.",
    )

    def _l10n_pt_get_down_payment_product(self):
        """
        The product put on the down payment lines of the company's invoices, created when first needed.
        Core leaves those lines without product, which a PT invoice cannot be posted with and the SAF-T
        (PT) cannot export (ProductCode and UnitOfMeasure are mandatory).
        """
        self.ensure_one()
        # sudo: whoever invoices a down payment (a salesman) may neither create products nor write the
        # company; the product is returned in the caller's environment
        company = self.sudo()
        product = company.l10n_pt_down_payment_product_id
        if not product.exists():
            product = self.env['product.product'].sudo().create({
                'name': 'Adiantamento',
                'default_code': 'ADIANTAMENTO',
                'type': 'service',
                'sale_ok': False,
                'purchase_ok': False,
                'taxes_id': [],
                'supplier_taxes_id': [],
                'company_id': company.id,
            })
            company.l10n_pt_down_payment_product_id = product
        return product.sudo(False)

    @api.model
    def _l10n_pt_sale_action_check_hash_integrity(self):
        return self.env.ref('l10n_pt_sale.action_l10n_pt_sale_report_hash_integrity').report_action(self.id)

    def _l10n_pt_sale_check_hash_integrity(self):
        if self.account_fiscal_country_id.code != 'PT':
            raise UserError(_('This feature is only available for Portuguese companies.'))
        return self.env['sale.order']._l10n_pt_check_hash_integrity(self)
