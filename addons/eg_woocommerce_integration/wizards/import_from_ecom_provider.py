import logging

from odoo import fields, models, api

_logging = logging.getLogger(__name__)


class ImportFromEComProvider(models.TransientModel):
    _inherit = 'import.from.ecom.provider'

    import_category_image = fields.Boolean(string='Category Image')
    import_customer_image = fields.Boolean(string='Customer Image')
    import_update_woo_tax_rate = fields.Boolean(string="Tax Rate",
                                                help="Update Tax Rate from WC to odoo and middle layer.")
    import_update_woo_payment_gateway = fields.Boolean(string="Payment Gateway",
                                                       help="Update Payment Gateway from WC to odoo and middle layer.")
    import_update_product_coupon = fields.Boolean(string="Product Coupon",
                                                  help="Update Coupon from WC to middle layer.")
    export_update_tax_rate = fields.Boolean(string="Tax Rate", help="Update Tax Rate odoo to WC at export")
    import_woo_tax_rate = fields.Boolean(string="Import Tax Rate",
                                         help="Import Tax Rate from WC to odoo and middle layer")
    import_woo_payment_gateway = fields.Boolean(string="Payment Gateway",
                                                help="Import Payment Gateway from WC to odoo and middle layer")
    import_woo_tax_class = fields.Boolean(string="Tax Class", help="Import Product from WC to odoo and middle layer")
    import_woo_product_coupon = fields.Boolean(string='Product Coupon',
                                               help="Import Tax Class from WC to middle layer")
    export_woo_tax_rate = fields.Boolean(string="Tax Rate", help="Export Tax Rate odoo to WC")
    export_woo_product_coupon = fields.Boolean(string="Product Coupon")

    def import_from_ecom_provider(self):
        if self.provider != "eg_woocommerce":
            return super(ImportFromEComProvider, self).import_from_ecom_provider()
        if self.import_product:
            self.env['eg.product.template'].import_product_template(self.ecom_instance_id)
        if self.import_product_attribute:
            self.env['eg.product.attribute'].import_attribute(self.ecom_instance_id)
        if self.import_product_attribute_value:
            self.env['eg.attribute.value'].import_product_attribute_terms(self.ecom_instance_id)
        if self.import_product_category:
            self.env['eg.product.category'].import_product_category(self.ecom_instance_id)
        if self.import_customer:
            self.env['eg.res.partner'].import_customer(self.ecom_instance_id)
        if self.import_sale_order:
            self.env['eg.sale.order'].import_woo_sale_order(self.ecom_instance_id)
        if self.import_woo_tax_rate:
            self.env['woo.tax.rate'].import_woo_tax_rate(self.ecom_instance_id)
        if self.import_woo_payment_gateway:
            self.env['eg.account.journal'].import_woo_payment_gateway(self.ecom_instance_id)
        if self.import_woo_tax_class:
            self.env['woo.tax.class'].import_woo_tax_class(self.ecom_instance_id)
        if self.import_woo_product_coupon:
            self.env['woo.product.coupon'].import_product_coupon(self.ecom_instance_id)
        if self.import_category_image:
            self.env['eg.product.category'].set_category_image(self.ecom_instance_id)
        if self.import_customer_image:
            self.env['eg.res.partner'].set_customer_image(self.ecom_instance_id)
        if self.import_product_tmpl_image:
            self.env['eg.product.template'].set_product_tmpl_image(self.ecom_instance_id)

        if self.export_product:
            self.env['eg.product.template'].woo_odoo_product_template_export(self.ecom_instance_id)
        if self.export_product_attribute:
            self.env['eg.product.attribute'].export_product_attribute(self.ecom_instance_id)
        if self.export_product_category:
            self.env['eg.product.category'].export_woo_product_category(self.ecom_instance_id)
        if self.export_product_attribute_value:
            self.env['eg.attribute.value'].export_woo_product_attribute_terms(self.ecom_instance_id)
        if self.export_woo_tax_rate:
            self.env['woo.tax.rate'].export_tax_rate(self.ecom_instance_id)
        if self.export_woo_product_coupon:
            self.env['woo.product.coupon'].export_product_coupon(self.ecom_instance_id)

        if self.import_update_product:
            self.env['eg.product.template'].import_update_woo_product_template(self.ecom_instance_id)
        if self.import_update_product_category:
            self.env['eg.product.category'].import_update_woo_product_category(self.ecom_instance_id)
        if self.import_update_product_attribute:
            self.env['eg.product.attribute'].import_update_product_attribute(self.ecom_instance_id)
        if self.import_update_product_attribute_value:
            self.env['eg.attribute.value'].import_update_attribute_terms(self.ecom_instance_id)
        if self.import_update_woo_tax_rate:
            self.env['woo.tax.rate'].import_update_tax_rate(self.ecom_instance_id)
        if self.import_update_woo_payment_gateway:
            self.env['eg.account.journal'].import_update_product_gateway(self.ecom_instance_id)
        if self.import_update_product_coupon:
            self.env['woo.product.coupon'].import_update_product_coupon(self.ecom_instance_id)

        if self.import_update_product_price:
            self.env['eg.product.template'].update_product_price(self.ecom_instance_id)
        if self.import_update_product_stock:
            self.env['eg.product.template'].update_product_stock(self.ecom_instance_id)

        if self.export_update_product_category:
            self.env['eg.product.category'].export_update_product_category(self.ecom_instance_id)
        if self.export_update_product_attribute:
            self.env['eg.product.attribute'].export_update_product_attribute(self.ecom_instance_id)
        if self.export_update_product_attribute_value:
            self.env['eg.attribute.value'].export_update_attribute_term(self.ecom_instance_id)
        if self.export_update_product:
            self.env['eg.product.template'].export_update_product_template_middle_to_wc(self.ecom_instance_id)
        if self.export_update_tax_rate:
            self.env['woo.tax.rate'].export_update_tax_rate(self.ecom_instance_id)
        if self.export_update_product_stock:
            self.env['eg.product.product'].update_woo_product_stock(instance_id=self.ecom_instance_id,
                                                                    from_date=self.export_stock_date)

    @api.onchange('import_product_category')
    def _onchange_import_woo_product_categories(self):
        if not self.import_product_category:
            self.import_category_image = False

    @api.onchange('import_customer')
    def _onchange_import_woo_customer(self):
        if not self.import_customer:
            self.import_customer_image = False

    @api.onchange('import_product')
    def _onchange_import_woo_product(self):
        if not self.import_product:
            self.import_product_tmpl_image = False
