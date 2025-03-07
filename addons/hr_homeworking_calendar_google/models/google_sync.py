import datetime
from dateutil import rrule

from odoo import models
from odoo.addons.google_calendar.utils.google_event import GoogleEvent


class GoogleSync(models.AbstractModel):
    _inherit = ['google.calendar.sync']

    def _get_skipped_google_events(self, gevents):
        """ Get skipped non-default Google Calendar events. """
        skipped_gevents = super()._get_skipped_google_events(gevents)
        non_default_gevents = [gevent for gevent in gevents if gevent.eventType not in ["default", "fromGmail"]]
        return GoogleEvent(skipped_gevents + non_default_gevents)

    def _pre_process_google_events(self, gevents):
        """ Pre-process working location Google Calendar events updating Employee records. """
        super()._pre_process_google_events(gevents)
        working_location_gevents = [gevent for gevent in gevents if gevent.eventType == 'workingLocation']
        if working_location_gevents:
            self._create_missing_working_locations(working_location_gevents, self.env.user)
            self._update_employee_working_locations(working_location_gevents, self.env.user)

    def _get_working_location_info(self, gevent):
        """
        Extract working location information from Google's gevent object.
        Returns a tuple of (location_type, odoo_location_type, location_name)
        """
        props = gevent.workingLocationProperties
        if props.get('customLocation') is not None:
            label = props['customLocation'].get('label', 'customLocation')
            return 'customLocation', 'other', label
        elif props.get('homeOffice') is not None:
            return 'homeOffice', 'home', 'Home'
        elif props.get('officeLocation') is not None:
            label = props['officeLocation'].get('label', 'Office')
            return 'officeLocation', 'office', label

    def _get_week_intersections_rrule(self, start_interval, end_interval, gevent):
        """ Retrieves the occurrences of a recurring event within a specified time interval. """
        start_rrule = self._get_date_from_google_str(gevent.start)
        if not start_rrule:
            return []

        rrule_obj = rrule.rrulestr(gevent.rrule, dtstart=start_rrule)
        return rrule_obj.between(start_interval, end_interval)

    def _get_date_from_google_str(self, date_dict):
        """ Converts a date dictionary from Google format to a datetime object. """
        if date_dict.get('dateTime'):
            return datetime.datetime.strptime(date_dict.get('dateTime'), '%Y-%m-%d %H:%M')
        elif date_dict.get('date'):
            return datetime.datetime.strptime(date_dict.get('date'), '%Y-%m-%d')
        else:
            return False

    def _create_missing_working_locations(self, working_location_gevents, user):
        """
        Create missing working locations in Odoo database.
        :param working_location_gevents: List of working location Google events
        :param user: The events' owner linked to the employee record to be updated.
        """
        existing_location_names = [loc.name for loc in self.env['hr.work.location'].search([])]

        for gevent in working_location_gevents:
            _, odoo_location_type, location_name = self._get_working_location_info(gevent)

            if location_name not in existing_location_names:
                self.env['hr.work.location'].create({
                    'name': location_name,
                    'location_type': odoo_location_type,
                    'address_id': user.partner_id.id,
                })
                existing_location_names += [location_name]

    def _update_employee_working_locations(self, gevents, user):
        """
        Update employee work locations based on working location Google events.
        :param gevents: List of working location Google events
        :param user: The events' owner linked to the employee record to be updated.
        """
        today = datetime.datetime.combine(datetime.datetime.now(), datetime.datetime.min.time())
        week_start = today - datetime.timedelta(days=today.weekday() + 1)
        week_end = week_start + datetime.timedelta(days=7)
        most_recent_location_per_weekday = {}

        for gevent in gevents:
            # Extract the date from the string received from Google (all day or datetime).
            date_str = gevent.start and (gevent.start.get('dateTime') or gevent.start.get('date'))
            _, _, location_name = self._get_working_location_info(gevent)
            odoo_location = self.env['hr.work.location'].search([('name', '=', location_name)])

            if gevent.rrule and any(freq in gevent.rrule for freq in ['UNTIL', 'COUNT', 'BYDAY']):  # Recurrent working location.
                intersections = self._get_week_intersections_rrule(week_start, week_end, gevent)

                # Handle events that start and finish in different days.
                start_date = self._get_date_from_google_str(gevent.start)
                end_date = self._get_date_from_google_str(gevent.end)
                while start_date.date() != end_date.date() and week_start <= start_date and start_date <= week_end:
                    most_recent_location_per_weekday[start_date.weekday()] = {
                        'date': start_date,
                        'odoo_location': odoo_location,
                    }
                    start_date += datetime.timedelta(days=1)

                # Handle event intersections with the current week.
                for date in intersections:
                    most_recent_location_per_weekday[date.weekday()] = {
                        'date': date,
                        'odoo_location': odoo_location,
                    }

            elif date_str:  # Exception working location.
                date = self._get_date_from_google_str(gevent.start)
                if date and week_start <= date and date <= week_end:
                    most_recent_location_per_weekday[date.weekday()] = {
                        'date': date,
                        'odoo_location': odoo_location,
                    }

        # Updating in the employee's record the most recent work location per weekdate (when defined).
        employee = self.env['hr.employee'].search([('user_id', '=', user.id)])
        if employee:
            update_dict = {}
            for i, day in enumerate(['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
                if most_recent_location_per_weekday.get(i):
                    update_dict[f'{day}_location_id'] = most_recent_location_per_weekday[i]['odoo_location']
            employee.write(update_dict)
