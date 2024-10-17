# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from .models.product import ProductProduct, ProductSupplierinfo
from .models.purchase import PurchaseOrder, PurchaseOrderGroup, PurchaseOrderLine
from .models.purchase_requisition import PurchaseRequisition, PurchaseRequisitionLine
from .models.res_config_settings import ResConfigSettings
from .wizard.purchase_requisition_alternative_warning import (
        PurchaseRequisitionAlternativeWarning,
)
from .wizard.purchase_requisition_create_alternative import (
        PurchaseRequisitionCreateAlternative,
)
