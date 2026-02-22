import datetime
from odoo import models
from odoo.addons.google_calendar.utils.google_event import GoogleEvent


class GoogleSync(models.AbstractModel):
    _inherit = 'google.calendar.sync'

    def _get_skipped_google_events(self, gevents):
        """ Filter out workingLocation events so they don't become Calendar Events. """
        ignored = [e for e in gevents if e.eventType == 'workingLocation']
        return super()._get_skipped_google_events(gevents) + GoogleEvent(ignored)

    def _pre_process_google_events(self, gevents):
        """ Update Employee locations based on Google events. """
        super()._pre_process_google_events(gevents)
        wl_gevents = [e for e in gevents if e.eventType == 'workingLocation']
        if wl_gevents:
            self._sync_employee_locations(wl_gevents, self.env.user)

    def _get_location_data(self, gevent):
        """ Extract (Odoo Type, Name) from Google event. """
        props = gevent.workingLocationProperties
        if props.get('type') == 'customLocation':
            return 'other', props['customLocation'].get('label', 'Custom')
        if props.get('type') == 'homeOffice':
            return 'home', 'Home'
        if props.get('type') == 'officeLocation':
            return 'office', props['officeLocation'].get('label', 'Office')
        return None, None

    def _sync_employee_locations(self, gevents, user):
        """ Create missing locations and update the employee record. """
        # 1. Identify necessary locations.
        google_loc_map = {}  # {gevent_id: name}
        required_names = set()
        for e in gevents:
            _, name = self._get_location_data(e)
            if name:
                google_loc_map[e.id] = name
                required_names.add(name)

        # 2. Batch create missing locations.
        existing = self.env['hr.work.location'].search([('name', 'in', list(required_names))])
        existing_map = {loc.name: loc for loc in existing}

        to_create = []
        for name in required_names:
            if name not in existing_map:
                # Find a sample event to deduce the type.
                ref_event = next(e for e in gevents if self._get_location_data(e)[1] == name)
                to_create.append({'name': name, 'location_type': self._get_location_data(ref_event)[0]})

        if to_create:
            new_recs = self.env['hr.work.location'].sudo().create(to_create)
            existing_map.update({rec.name: rec for rec in new_recs})

        # 3. Update Employee (using singleEvents=True).
        updates = {}
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for e in gevents:
            dt_str = e.start.get('date') or e.start.get('dateTime', '')[:10]
            if dt_str and google_loc_map.get(e.id) in existing_map:
                dt = datetime.date.fromisoformat(dt_str)
                updates[f"{days[dt.weekday()]}_location_id"] = existing_map[google_loc_map[e.id]].id

        if updates and user.employee_id:
            user.employee_id.sudo().write(updates)
