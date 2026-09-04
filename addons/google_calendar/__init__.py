# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import utils
from . import wizard


def remove_unimported_calendars(env):
    # When syncing calendars from google to odoo, we first create 'ghost records', and only import them once the user
    # enables their sync. These ghost records should be removed otherwise they will be visible in the UI after the uninstall.
    calendars_to_remove = env['calendar.calendar'].with_context(active_test=False).search([('is_import_pending', '=', True)])
    calendars_to_remove.google_id = False  # This makes sure the calendar is deleted instead of archived
    calendars_to_remove.unlink()
