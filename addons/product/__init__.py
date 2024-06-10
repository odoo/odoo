# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from .models import (
    ProductTemplate,
    ProductProduct,
    ProductAttributeCustomValue,
    ProductCatalogMixin,
    ProductDocument,
    ProductPackaging,
    Pricelist,
)
from . import report
from . import populate
from . import wizard
