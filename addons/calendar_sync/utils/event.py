from collections import namedtuple, UserDict

# --------------------------------------------------------------------------
# The ProviderData structure contains events coming from a provider, sorted
# by kind of update (added/updated/removed) and then by kind of events (
# single, recurrence).
# Then, each item is a ProviderEvent containing event data in the provider data
# format.
# --------------------------------------------------------------------------
ProviderData = namedtuple('ProviderData', ['added', 'updated', 'removed'])
ProviderEvents = namedtuple('ProviderEvents', ['singles', 'recurrences'])

class ProviderEvent(UserDict):
    """
    A provider event implemented as a dictionary with some specific methods
    which should be overriden for each calendar provider.
    """

    def set_odoo_event(self, odoo_event):
        """
        Set the Odoo event linked to the external calendar event.
        """
        self['_odoo'] = odoo_event

    def get_odoo_event(self):
        """
        Get the Odoo event linked to the external calendar event.
        """
        return self.get('_odoo')

    def has_odoo_event(self):
        """
        Indicates if the external calendar event is linked to an Odoo event.
        """
        return bool(self.get('_odoo'))

    def is_single_event(self) -> bool:
        """
        Indicates if it is a single event instance.
        """
        raise Exception("Not overriden")

    def is_recurrence(self) -> bool:
        """
        Indicates if it is a recurrence.
        """
        raise Exception("Not overriden")

    def is_recurrent(self) -> bool:
        """
        Indicates if the event is part of a recurrence.
        """
        raise Exception("Not overriden")

    def is_occurrence(self) -> bool:
        """
        Indicates if it is an event which is recurrent (i.e part of a recurrence).
        """
        raise Exception("Not overriden")

    def is_exception(self) -> bool:
        """
        Indicates if it is an event which is recurrent but not par of the recurrence anymore.
        """
        raise Exception("Not overriden")

    def is_removed(self) -> bool:
        """
        Indicates if the event is removed.
        """
        raise Exception("Not overriden")

    def odoo_owner(self, env):
        """
        Indicates who is the Odoo user who owns the event (i.e the organizer of the event).
        """
        raise Exception("Not overriden")
