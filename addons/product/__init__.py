# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from .models.decimal_precision import DecimalPrecision
from .models.ir_attachment import IrAttachment
from .models.product_attribute import ProductAttribute
from .models.product_attribute_custom_value import ProductAttributeCustomValue
from .models.product_attribute_value import ProductAttributeValue
from .models.product_catalog_mixin import ProductCatalogMixin
from .models.product_category import ProductCategory
from .models.product_combo import ProductCombo
from .models.product_combo_item import ProductComboItem
from .models.product_document import ProductDocument
from .models.product_packaging import ProductPackaging
from .models.product_pricelist import ProductPricelist
from .models.product_pricelist_item import ProductPricelistItem
from .models.product_product import ProductProduct
from .models.product_supplierinfo import ProductSupplierinfo
from .models.product_tag import ProductTag
from .models.product_template import ProductTemplate
from .models.product_template_attribute_exclusion import ProductTemplateAttributeExclusion
from .models.product_template_attribute_line import ProductTemplateAttributeLine
from .models.product_template_attribute_value import ProductTemplateAttributeValue
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.res_country_group import ResCountryGroup
from .models.res_currency import ResCurrency
from .models.res_partner import ResPartner
from .models.uom_uom import UomUom
from .report.product_label_report import (
    ReportProductReport_Producttemplatelabel2x7,
    ReportProductReport_Producttemplatelabel4x12,
    ReportProductReport_Producttemplatelabel4x12noprice,
    ReportProductReport_Producttemplatelabel4x7,
    ReportProductReport_Producttemplatelabel_Dymo,
)
from .report.product_pricelist_report import ReportProductReport_Pricelist
from .wizard.product_label_layout import ProductLabelLayout
from .wizard.update_product_attribute_value import UpdateProductAttributeValue
