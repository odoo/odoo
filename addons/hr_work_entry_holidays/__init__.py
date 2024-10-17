# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from .models.hr_contract import HrContract
from .models.hr_leave import HrLeave, HrLeaveType
from .models.hr_work_entry import HrWorkEntry, HrWorkEntryType


def _validate_existing_work_entry(env):
    env['hr.work.entry'].search([])._check_if_error()
