from odoo import models


WEBSITE_SALE_SETTINGS_FIELDS = (
    "shop_page_container",
    "shop_ppg",
    "shop_ppr",
    "shop_gap",
    "shop_opt_products_design_classes",
    "shop_default_sort",
    "product_page_container",
    "product_page_cols_order",
    "product_page_image_layout",
    "product_page_image_width",
    "product_page_image_spacing",
    "product_page_image_roundness",
    "product_page_image_ratio",
    "product_page_image_ratio_mobile",
    "product_page_grid_columns",
)


class WebsiteExportWizard(models.TransientModel):
    _inherit = "website.export.wizard"

    def _get_website_settings_fields(self):
        return WEBSITE_SALE_SETTINGS_FIELDS


class WebsiteImportWizard(models.TransientModel):
    _inherit = "website.import.wizard"

    def _get_website_settings_fields(self):
        return WEBSITE_SALE_SETTINGS_FIELDS
