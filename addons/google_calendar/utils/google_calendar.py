from odoo.addons.google_calendar.utils.google_api_resource import GoogleApiResource


class GoogleCalendar(GoogleApiResource):
    """This helper class holds the values of a Google calendar.
    Inspired by Odoo recordset, one instance can be a single Google calendar or a
    (immutable) set of Google calendars.
    All usual set operations are supported (union, intersection, etc.).

    A list of all attributes can be found in the API documentation.
    https://developers.google.com/workspace/calendar/api/v3/reference/calendars#resource-representations

    :param iterable: Iterable of GoogleCalendar instances or iterable of dictionaries

    """

    def _get_model(self, env):
        return env['calendar.calendar']

    def get_odoo_calendar(self, env):
        return env['calendar.calendar'].browse(self.odoo_id(self.env))

    def exists(self, env):
        self.odoo_ids(env)  # Load matching Ids
        return self.filter(lambda c: c._odoo_id)

    def get_deleted(self):
        return self.filter(lambda c: c.deleted)

    def get_primary(self):
        return self.filter(lambda c: c.primary)
