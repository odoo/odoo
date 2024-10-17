# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import utils
from . import wizard

from .models.calendar import CalendarEvent
from .models.calendar_attendee import CalendarAttendee
from .models.calendar_recurrence_rule import CalendarRecurrence
from .models.microsoft_sync import MicrosoftCalendarSync
from .models.res_config_settings import ResConfigSettings
from .models.res_users import ResUsers
from .models.res_users_settings import ResUsersSettings
from .wizard.reset_account import MicrosoftCalendarAccountReset

import uuid


def init_initiating_microsoft_uuid(env):
    """ Sets the company name as the default value for the initiating
    party name on all existing companies once the module is installed. """
    config_parameter = env['ir.config_parameter'].sudo()
    microsoft_guid = config_parameter.get_param('microsoft_calendar.microsoft_guid', False)
    if not microsoft_guid:
        config_parameter.set_param('microsoft_calendar.microsoft_guid', str(uuid.uuid4()))
