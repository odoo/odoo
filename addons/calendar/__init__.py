# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard

from .models.calendar_alarm import CalendarAlarm
from .models.calendar_alarm_manager import CalendarAlarm_Manager
from .models.calendar_attendee import CalendarAttendee
from .models.calendar_event import CalendarEvent
from .models.calendar_event_type import CalendarEventType
from .models.calendar_filter import CalendarFilters
from .models.calendar_recurrence import CalendarRecurrence
from .models.ir_http import IrHttp
from .models.mail_activity import MailActivity
from .models.mail_activity_mixin import MailActivityMixin
from .models.mail_activity_type import MailActivityType
from .models.res_partner import ResPartner
from .models.res_users import ResUsers
from .models.res_users_settings import ResUsersSettings
from .wizard.calendar_popover_delete_wizard import CalendarPopoverDeleteWizard
from .wizard.calendar_provider_config import CalendarProviderConfig
from .wizard.mail_activity_schedule import MailActivitySchedule
