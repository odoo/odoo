from odoo import models, fields, api


class ImportFromEComProvider(models.TransientModel):
    _name = "import.from.ecom.provider"

    ecom_instance_id = fields.Many2one(comodel_name="eg.ecom.instance", string="Instance", required=True)
    provider = fields.Selection(related="ecom_instance_id.provider", store=True)
    mapping_type = fields.Selection([("import", "Import"), ("export", "Export"), ("update_import", "Update/Import"),
                                     ("update_export", "Update/Export")], string="Type", store=True, required=True)
    # add by akash

    # Import
    import_product = fields.Boolean(string='Product', help="Import Product from eCOm to odoo and middle layer")
    import_product_category = fields.Boolean(string="Product Category",
                                             help="Import Category from eCOm to odoo and middle layer")
    import_customer = fields.Boolean(string="Customer", help="Import Customer from eCOm to odoo and middle layer")
    import_sale_order = fields.Boolean(string="Sale Order",
                                       help="Import Sale Order from eCOm to odoo and middle layer")
    import_product_attribute = fields.Boolean(string='Product Attribute',
                                              help="Import Attribute from eCOm to odoo and middle layer")
    import_product_attribute_value = fields.Boolean(string="Attribute Values",
                                                    help="Import Attribute Terms from eCOm to odoo and middle layer")
    import_product_tmpl_image = fields.Boolean(string='Product Image')

    # Export
    export_product = fields.Boolean(string='Products', help="Export product middle layer to eCom")
    export_product_attribute = fields.Boolean(string="Product Attribute",
                                              help="Export attribute odoo to eCom")
    export_product_attribute_value = fields.Boolean(string="Product Attribute Terms",
                                                    help="Export  Attribute Terms odoo to eCom")
    export_product_category = fields.Boolean(string="Product Category", help="Export Category odoo to eCom")

    # Update/Import
    import_update_product = fields.Boolean(string="Products",
                                           help="Update product from eCom to odoo and middle layer.")
    import_update_product_category = fields.Boolean(string="Product Category",
                                                    help="Update Category from eCom to odoo and middle layer.")
    import_update_product_attribute = fields.Boolean(string="Product Attribute",
                                                     help="Update Attribute from eCom to odoo and middle layer.")
    import_update_product_attribute_value = fields.Boolean(string="Product Attribute Terms",
                                                           help="Update Attribute Terms from eCom to odoo and middle layer.")
    import_update_product_price = fields.Boolean(string="Update Product Price",
                                                 help="Update product Price from eCom to odoo and middle layer.")
    import_update_product_stock = fields.Boolean(string='Update Product Stock',
                                                 help="Update product Stock from eCom to odoo and middle layer.")

    # Update/Export
    export_update_product_category = fields.Boolean(string="Product Category",
                                                    help="Update Category odoo to eCom at export")
    export_update_product_attribute = fields.Boolean(string="Product Attribute",
                                                     help="Update Attribute odoo to eCom at export")
    export_update_product_attribute_value = fields.Boolean(string="Product Attribute Terms",
                                                           help="Update Attribute Terms odoo to eCom at export")
    export_update_product = fields.Boolean(string="Product",
                                           help="Update pProduct middle layer to eCom at export")
    export_update_product_stock = fields.Boolean(string="Product Stock", help="Update product stock odoo to eCom")
    export_stock_date = fields.Datetime(string="From Date", help="Stcok update if any changes in stock after this date")

    def import_from_ecom_provider(self):
        a = ""
