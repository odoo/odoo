# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .models import (
    EventEvent, EventEventTicket, EventRegistration, ProductTemplate, SaleOrder,
    SaleOrderLine,
)
from .report import EventSaleReport
from .wizard import EventEventConfigurator, RegistrationEditor, RegistrationEditorLine
