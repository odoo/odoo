from datetime import datetime, date

from odoo import models
from odoo.addons.hr.models.hr_employee_location import DAYS
from odoo.addons.google_calendar.utils.google_event import GoogleEvent


class GoogleSync(models.AbstractModel):
    _inherit = 'google.calendar.sync'

    def _pre_process_google_events(self, gevents):
        """ Update Employee locations based on Google events. """
        super()._pre_process_google_events(gevents)
        sparse_cancelled_ids = [e.id for e in gevents if e.is_cancelled() and not e.eventType]
        linked_cancelled_ids = set(self.env['hr.employee.location'].sudo().search([
            ('google_id', 'in', sparse_cancelled_ids),
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
        EmployeeLocation = self.env['hr.employee.location'].sudo().with_context(active_test=False)
        cancelled_google_ids = [e.id for e in gevents if e.is_cancelled()]
        if cancelled_google_ids:
            EmployeeLocation.search([('google_id', 'in', cancelled_google_ids)])._cancel()
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

        if not user.employee_id:
            return

        # 3. Map recurring events to weekly defaults and single events to dated exceptions.
        weekly_updates = {}
        for location_data, evs in gevents_by_location_data.items():
            if location_data in work_location_by_location_data:
                loc_id = work_location_by_location_data[location_data].id
                for e in evs:
                    dt_str = e.start.get('date') or e.start.get('dateTime')
                    if dt_str:
                        dt = datetime.fromisoformat(dt_str).date() if 'T' in dt_str else date.fromisoformat(dt_str)
                        google_location = EmployeeLocation.search([('google_id', '=', e.id)], limit=1)
                        if e.is_recurrent():
                            weekly_updates[DAYS[dt.weekday()]] = loc_id
                            if google_location:
                                google_location._cancel()
                            continue
                        dated_location = EmployeeLocation.search([
                            ('employee_id', '=', user.employee_id.id),
                            ('date', '=', dt),
                        ], limit=1)
                        vals = {
                            'date': dt,
                            'employee_id': user.employee_id.id,
                            'work_location_id': loc_id,
                            'google_id': e.id,
                            'need_sync': False,
                            'active': True,
                        }
                        if google_location:
                            if dated_location and dated_location != google_location:
                                dated_location.unlink()
                            google_location.write(vals)
                        elif dated_location:
                            dated_location.write(vals)
                        else:
                            EmployeeLocation.create(vals)
        if weekly_updates:
            user.employee_id.sudo().write(weekly_updates)
