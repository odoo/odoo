# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from .models.hr_contract import HrContract
from .models.hr_employee import HrEmployee
from .models.hr_work_entry import HrWorkEntry, HrWorkEntryType
from .models.resource_calendar import ResourceCalendar
from .wizard.hr_work_entry_regeneration_wizard import HrWorkEntryRegenerationWizard
