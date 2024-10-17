# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from .models.equipment import MaintenanceEquipment, MaintenanceRequest
from .models.res_users import HrEmployee, ResUsers
from .wizard.hr_departure_wizard import HrDepartureWizard
