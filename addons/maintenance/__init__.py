# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from .models.maintenance import (
    MaintenanceEquipment, MaintenanceEquipmentCategory,
    MaintenanceMixin, MaintenanceRequest, MaintenanceStage, MaintenanceTeam,
)
from .models.res_config_settings import ResConfigSettings
