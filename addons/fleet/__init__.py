# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report
from . import wizard

from .models.fleet_service_type import FleetServiceType
from .models.fleet_vehicle import FleetVehicle
from .models.fleet_vehicle_assignation_log import FleetVehicleAssignationLog
from .models.fleet_vehicle_log_contract import FleetVehicleLogContract
from .models.fleet_vehicle_log_services import FleetVehicleLogServices
from .models.fleet_vehicle_model import FleetVehicleModel
from .models.fleet_vehicle_model_brand import FleetVehicleModelBrand
from .models.fleet_vehicle_model_category import FleetVehicleModelCategory
from .models.fleet_vehicle_odometer import FleetVehicleOdometer
from .models.fleet_vehicle_state import FleetVehicleState
from .models.fleet_vehicle_tag import FleetVehicleTag
from .models.res_config_settings import ResConfigSettings
from .models.res_partner import ResPartner
from .report.fleet_report import FleetVehicleCostReport
from .wizard.fleet_vehicle_send_mail import FleetVehicleSendMail
