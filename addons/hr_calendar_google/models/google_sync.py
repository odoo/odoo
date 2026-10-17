from datetime import datetime, date

from odoo import api, models
from odoo.fields import Domain

from odoo.addons.google_calendar.utils.google_event import GoogleEvent
from odoo.addons.hr.models.hr_employee_location import DAYS


class GoogleEventSync(models.AbstractModel):
    _inherit = 'google.event.sync'

    @api.model
    def _sync_google2odoo(self, google_events, calendar, write_dates=None, default_reminders=()):
        # Shared calendars can contain another employee's working locations.
        sync = self.with_context(hr_google_sync_work_locations=calendar == self.env.user.primary_calendar_id)
        return super(GoogleEventSync, sync)._sync_google2odoo(
            google_events, calendar, write_dates, default_reminders,
        )

    def _pre_process_google_events(self, gevents):
        """ Update Employee locations based on Google events. """
        super()._pre_process_google_events(gevents)
        if not self.env.context.get('hr_google_sync_work_locations', True):
            return
        sparse_cancelled_ids = [e.id for e in gevents if e.is_cancelled() and not e.eventType]
        linked_cancelled_ids = set(self.env['hr.employee.location'].search([
            ('google_id', 'in', sparse_cancelled_ids),
            ('employee_id', '=', self.env.user.employee_id.id),
        ]).mapped('google_id'))
        working_location_gevents = [
            e for e in gevents
            if e.eventType == 'workingLocation' or e.id in linked_cancelled_ids
        ]
        if working_location_gevents:
            self._sync_employee_locations(working_location_gevents, self.env.user)

    def _get_skipped_google_events(self, gevents):
        """ Filter out workingLocation events so they don't become Calendar Events. """
        ignored_gevents = [e for e in gevents if e.eventType == 'workingLocation']
        return super()._get_skipped_google_events(gevents) + GoogleEvent(ignored_gevents)

    def _get_location_data(self, gevent):
        """ Extract (Odoo Type, Name) from Google event. """
        props = gevent.workingLocationProperties
        if props.get('type') == 'customLocation':
            return 'other', props['customLocation'].get('label', self.env._('Custom'))
        if props.get('type') == 'homeOffice':
            return 'home', self.env._('Home')
        if props.get('type') == 'officeLocation':
            return 'office', props['officeLocation'].get('label', self.env._('Office'))
        return None, None

    def _sync_employee_locations(self, gevents, user):
        """ Create missing locations and update the employee record. """
        employee = user.employee_id
        if not employee:
            return
        EmployeeLocation = self.env['hr.employee.location']
        cancelled_google_ids = [e.id for e in gevents if e.is_cancelled()]
        if cancelled_google_ids:
            EmployeeLocation.search([
                ('google_id', 'in', cancelled_google_ids),
                ('employee_id', '=', employee.id),
            ])._cancel()
        gevents = [e for e in gevents if not e.is_cancelled()]

        # 1. Create a map with the gevents by location and a map with the location name by their type.
        gevents_by_location_data = {}
        for e in gevents:
            location_data = self._get_location_data(e)
            if location_data[1]:
                gevents_by_location_data.setdefault(location_data, []).append(e)
        existing = self.env['hr.work.location'].search([('name', 'in', [loc[1] for loc in gevents_by_location_data])])
        work_location_by_location_data = {(loc.location_type, loc.name): loc for loc in existing}

        # 2. List working locations to be created, create them and update the location map.
        to_create = []
        for location_data in gevents_by_location_data:
            if location_data not in work_location_by_location_data:
                location_type, name = location_data
                to_create.append({'name': name, 'location_type': location_type})
        if to_create:
            new_recs = self.env['hr.work.location'].sudo().create(to_create)
            work_location_by_location_data.update({(rec.location_type, rec.name): rec for rec in new_recs})

        # 3. Prepare recurring events and dated exceptions.
        weekly_updates = {}
        event_data = []
        for location_data, evs in gevents_by_location_data.items():
            if location_data in work_location_by_location_data:
                loc_id = work_location_by_location_data[location_data].id
                for e in evs:
                    dt_str = e.start.get('date') or e.start.get('dateTime')
                    if dt_str:
                        dt = datetime.fromisoformat(dt_str).date() if 'T' in dt_str else date.fromisoformat(dt_str)
                        event_data.append((e, dt, loc_id))

        # 4. Write the working location updates in the employee record.
        if event_data:
            google_ids = [e.id for e, _dt, _loc_id in event_data]
            dates = [dt for e, dt, _loc_id in event_data if not e.is_recurrent()]
            employee_locations = EmployeeLocation.search(
                Domain('employee_id', '=', employee.id)
                & (Domain('google_id', 'in', google_ids) | Domain('date', 'in', dates))
            )
            locations_by_google_id = {loc.google_id: loc for loc in employee_locations if loc.google_id}
            locations_by_date = {loc.date: loc for loc in employee_locations if loc.date}

            to_cancel = EmployeeLocation
            to_create_by_date = {}
            for e, dt, loc_id in event_data:
                if e.is_recurrent():
                    weekly_updates[DAYS[dt.weekday()]] = loc_id
                    to_cancel |= locations_by_google_id.get(e.id, EmployeeLocation)
                    continue
                vals = {
                    'date': dt,
                    'employee_id': employee.id,
                    'work_location_id': loc_id,
                    'google_id': e.id,
                    'need_sync': False,
                }
                google_location = locations_by_google_id.get(e.id, EmployeeLocation)
                dated_location = locations_by_date.get(dt, EmployeeLocation)
                if google_location:
                    (dated_location - google_location).unlink()
                    google_location.write(vals)
                elif dated_location:
                    dated_location.write(vals)
                else:
                    to_create_by_date[dt] = vals
            to_cancel._cancel()
            if to_create_by_date:
                EmployeeLocation.create(list(to_create_by_date.values()))
        if weekly_updates:
            employee.sudo().write(weekly_updates)
