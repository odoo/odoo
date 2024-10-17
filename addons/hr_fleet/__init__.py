# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from .models.employee import HrEmployee, HrEmployeePublic
from .models.fleet_vehicle import FleetVehicle
from .models.fleet_vehicle_assignation_log import FleetVehicleAssignationLog
from .models.fleet_vehicle_log_contract import FleetVehicleLogContract
from .models.fleet_vehicle_log_services import FleetVehicleLogServices
from .models.fleet_vehicle_odometer import FleetVehicleOdometer
from .models.mail_activity_plan_template import MailActivityPlanTemplate
from .models.res_users import ResUsers
from .wizard.hr_departure_wizard import HrDepartureWizard
