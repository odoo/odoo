# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from datetime import datetime

from odoo.addons.mail.tests.common import MailCase
from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService
from odoo.tests import tagged

from odoo.addons.microsoft_calendar.tests.common import TestCommon


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestSyncOdoo2MicrosoftMail(TestCommon, MailCase):

    def test_imported_events_have_primary_calendar_id(self):
        pass

    def update_does_not_overwrite_falsy_calendar_id(self):
        pass

    def moving_an_event_to_a_secondary_calendar_removes_it_from_outlook(self):
        pass
