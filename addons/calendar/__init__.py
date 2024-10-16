# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import (
    CalendarAlarm, CalendarAlarm_Manager, CalendarAttendee, CalendarEvent,
    CalendarEventType, CalendarFilters, CalendarRecurrence, IrHttp, MailActivity,
    MailActivityMixin, MailActivityType, ResPartner, ResUsers, ResUsersSettings,
)
from .wizard import CalendarPopoverDeleteWizard, CalendarProviderConfig, MailActivitySchedule
