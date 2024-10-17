# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report
from . import wizard

from .models.event_event import EventEvent
from .models.event_registration import EventRegistration
from .models.event_ticket import EventEventTicket
from .models.product_template import ProductTemplate
from .models.sale_order import SaleOrder
from .models.sale_order_line import SaleOrderLine
from .report.event_sale_report import EventSaleReport
from .wizard.event_configurator import EventEventConfigurator
from .wizard.event_edit_registration import RegistrationEditor, RegistrationEditorLine
