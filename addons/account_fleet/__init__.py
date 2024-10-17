# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from .models.account_move import AccountMove, AccountMoveLine
from .models.fleet_vehicle import FleetVehicle
from .models.fleet_vehicle_log_services import FleetVehicleLogServices
from .wizard.account_automatic_entry_wizard import AccountAutomaticEntryWizard
