# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import (
    DecimalPrecision, IrAttachment, ProductAttribute, ProductAttributeCustomValue,
    ProductAttributeValue, ProductCatalogMixin, ProductCategory, ProductCombo, ProductComboItem,
    ProductDocument, ProductPackaging, ProductPricelist, ProductPricelistItem, ProductProduct,
    ProductSupplierinfo, ProductTag, ProductTemplate, ProductTemplateAttributeExclusion,
    ProductTemplateAttributeLine, ProductTemplateAttributeValue, ResCompany, ResConfigSettings,
    ResCountryGroup, ResCurrency, ResPartner, UomUom,
)
from .report import (
    ReportProductReport_Pricelist, ReportProductReport_Producttemplatelabel2x7,
    ReportProductReport_Producttemplatelabel4x12,
    ReportProductReport_Producttemplatelabel4x12noprice,
    ReportProductReport_Producttemplatelabel4x7, ReportProductReport_Producttemplatelabel_Dymo,
)
from .wizard import ProductLabelLayout, UpdateProductAttributeValue
