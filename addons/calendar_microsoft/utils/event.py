from odoo.addons.calendar_sync.utils.event import ProviderEvent

class MicrosoftEvent(ProviderEvent):

    def __getattr__(self, name):
        return self.get(name)

    def is_single_event(self) -> bool:
        """
        Indicates if it is a single event instance.
        """
        raise Exception("Not overriden")

    def is_recurrence(self) -> bool:
        """
        Indicates if it is a recurrence.
        """
        return self.get('type') == 'seriesMaster'

    def is_recurrent(self) -> bool:
        """
        Indicates if the event is part of a recurrence.
        """
        return self.get('type') in ('occurrence', 'exception')

    def is_occurrence(self) -> bool:
        """
        Indicates if the event is part of a recurrence.
        """
        return bool(self.seriesMasterId)

    def is_exception(self) -> bool:
        """
        Indicates if the event is recurrent but not part of the recurrence anymore.
        """
        return self.get('type') == 'exception'

    def is_removed(self) -> bool:
        """
        Indicates if the event is removed.
        """
        return self.get('@removed') and self.get('@removed').get('reason') == 'deleted'

    def odoo_owner(self, env):
        """
        Indicates who is the owner of an event (i.e the organizer of the event).

        There are several possible cases:
        1) the current Odoo user is the organizer of the event according to Outlook event, so return his id.
        2) the current Odoo user is NOT the organizer and:
           2.1) we are able to find a Odoo user using the Outlook event organizer email address and we use his id,
           2.2) we are NOT able to find a Odoo user matching the organizer email address and we return False, meaning
                that no Odoo user will be able to modify this event. All modifications will be done from Outlook.
        """
        if self.isOrganizer:
            return env.user.id
        if self.organizer.get('emailAddress') and self.organizer.get('emailAddress').get('address'):
            # Warning: In Microsoft: 1 email = 1 user; but in Odoo several users might have the same email
            user = env['res.users'].search([('email', '=', self.organizer.get('emailAddress').get('address'))], limit=1)
            return user.id if user else False
        return False
