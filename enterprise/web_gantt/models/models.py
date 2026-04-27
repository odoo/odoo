# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import datetime, timezone, timedelta
from lxml.builder import E

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import _, unique, OrderedSet


class Base(models.AbstractModel):
    _inherit = 'base'

    _start_name = 'date_start'       # start field to use for default gantt view
    _stop_name = 'date_stop'         # stop field to use for default gantt view

    # action_gantt_reschedule utils
    _WEB_GANTT_RESCHEDULE_FORWARD = 'forward'
    _WEB_GANTT_RESCHEDULE_BACKWARD = 'backward'
    _WEB_GANTT_LOOP_ERROR = 'loop_error'
    _WEB_GANTT_NO_POSSIBLE_ACTION_ERROR = 'no_possible_action_error'

    @api.model
    def _get_default_gantt_view(self):
        """ Generates a default gantt view by trying to infer
        time-based fields from a number of pre-set attribute names

        :returns: a gantt view
        :rtype: etree._Element
        """
        view = E.gantt(string=self._description)

        gantt_field_names = {
            '_start_name': ['date_start', 'start_date', 'x_date_start', 'x_start_date'],
            '_stop_name': ['date_stop', 'stop_date', 'date_end', 'end_date', 'x_date_stop', 'x_stop_date', 'x_date_end', 'x_end_date'],
        }
        for name in gantt_field_names.keys():
            if getattr(self, name) not in self._fields:
                for dt in gantt_field_names[name]:
                    if dt in self._fields:
                        setattr(self, name, dt)
                        break
                else:
                    raise UserError(_("Insufficient fields for Gantt View!"))
        view.set('date_start', self._start_name)
        view.set('date_stop', self._stop_name)

        return view

    @api.model
    def get_gantt_data(self, domain, groupby, read_specification, limit=None, offset=0, unavailability_fields=None, progress_bar_fields=None, start_date=None, stop_date=None, scale=None):
        """
        Returns the result of a read_group (and optionally search for and read records inside each
        group), and the total number of groups matching the search domain.

        :param domain: search domain
        :param groupby: list of field to group on (see ``groupby``` param of ``read_group``)
        :param read_specification: web_read specification to read records within the groups
        :param limit: see ``limit`` param of ``read_group``
        :param offset: see ``offset`` param of ``read_group``
        :param boolean unavailability_fields
        :param string start_date: start datetime in utc, e.g. "2024-06-22 23:00:00"
        :param string stop_date: stop datetime in utc
        :param string scale: among "day", "week", "month" and "year"
        :return: {
            'groups': [
                {
                    '<groupby_1>': <value_groupby_1>,
                    ...,
                    '__record_ids': [<ids>]
                }
            ],
            'records': [<record data>]
            'length': total number of groups
            'unavailabilities': {
                '<unavailability_fields_1>': <value_unavailability_fields_1>,
                ...
            }
            'progress_bars': {
                '<progress_bar_fields_1>': <value_progress_bar_fields_1>,
                ...
            }
        }
        """
        # TODO: group_expand doesn't currently respect the limit/offset
        lazy = not limit and not offset and len(groupby) == 1
        # Because there is no limit by group, we can fetch record_ids as aggregate
        final_result = self.web_read_group(
            domain, ['__record_ids:array_agg(id)'], groupby,
            limit=limit, offset=offset, lazy=lazy,
        )

        all_record_ids = tuple(unique(
            record_id
            for one_group in final_result['groups']
            for record_id in one_group['__record_ids']
        ))

        # Do search_fetch to order records (model order can be no-trivial)
        all_records = self.with_context(active_test=False).search_fetch([('id', 'in', all_record_ids)], read_specification.keys())
        final_result['records'] = all_records.with_env(self.env).web_read(read_specification)

        if unavailability_fields is None:
            unavailability_fields = []
        if progress_bar_fields is None:
            progress_bar_fields = []

        ordered_set_ids = OrderedSet(all_records._ids)
        res_ids_for_unavailabilities = defaultdict(set)
        res_ids_for_progress_bars = defaultdict(set)
        for group in final_result['groups']:
            for field in unavailability_fields:
                res_id = group[field][0] if group[field] else False
                if res_id:
                    res_ids_for_unavailabilities[field].add(res_id)
            for field in progress_bar_fields:
                res_id = group[field][0] if group[field] else False
                if res_id:
                    res_ids_for_progress_bars[field].add(res_id)
            # Reorder __record_ids
            group['__record_ids'] = list(ordered_set_ids & OrderedSet(group['__record_ids']))
            # We don't need these in the gantt view
            del group['__domain']
            del group[f'{groupby[0]}_count' if lazy else '__count']
            group.pop('__fold', None)

        if unavailability_fields or progress_bar_fields:
            start, stop = fields.Datetime.from_string(start_date), fields.Datetime.from_string(stop_date)

        unavailabilities = {}
        for field in unavailability_fields:
            unavailabilities[field] = self._gantt_unavailability(field, list(res_ids_for_unavailabilities[field]), start, stop, scale)
        final_result['unavailabilities'] = unavailabilities

        progress_bars = {}
        for field in progress_bar_fields:
            progress_bars[field] = self._gantt_progress_bar(field, list(res_ids_for_progress_bars[field]), start, stop)
        final_result['progress_bars'] = progress_bars

        return final_result

    @api.model
    def web_gantt_reschedule(
        self,
        direction,
        master_record_id, slave_record_id,
        dependency_field_name, dependency_inverted_field_name,
        start_date_field_name, stop_date_field_name
    ):
        """ Reschedule a record according to the provided parameters.

            :param direction: The direction of the rescheduling 'forward' or 'backward'
            :param master_record_id: The record that the other one is depending on.
            :param slave_record_id: The record that is depending on the other one.
            :param dependency_field_name: The field name of the relation between the master and slave records.
            :param dependency_inverted_field_name: The field name of the relation between the slave and the parent
                   records.
            :param start_date_field_name: The start date field used in the gantt view.
            :param stop_date_field_name: The stop date field used in the gantt view.
            :return: dict = {
                type: notification type,
                message: notification message,
                old_vals_per_pill_id: dict = {
                    pill_id: {
                        start_date_field_name: planned_date_begin before rescheduling
                        stop_date_field_name: date_deadline before rescheduling
                    }
                }
            }
        """

        if direction not in (self._WEB_GANTT_RESCHEDULE_FORWARD, self._WEB_GANTT_RESCHEDULE_BACKWARD):
            raise ValueError("Invalid direction %r" % direction)

        master_record, slave_record = self.env[self._name].browse([master_record_id, slave_record_id])

        search_domain = [(dependency_field_name, 'in', master_record.id), ('id', '=', slave_record.id)]
        if not self.env[self._name].search_count(search_domain, limit=1):
            raise ValueError("Record '%r' is not a parent record of '%r'" % (master_record.name, slave_record.name))

        if not self._web_gantt_reschedule_is_relation_candidate(
                master_record, slave_record, start_date_field_name, stop_date_field_name):
            return {
                'type': 'warning',
                'message': _('You cannot reschedule %(main_record)s towards %(other_record)s.',
                             main_record=master_record.name, other_record=slave_record.name),
            }

        is_master_prior_to_slave = master_record[stop_date_field_name] <= slave_record[start_date_field_name]

        # When records are in conflict, record that is moved is the other one than when there is no conflict.
        # This might seem strange at first sight but has been decided during first implementation as when in conflict,
        # and especially when the distance between the pills is big, the arrow is interpreted differently as it comes
        # from the right to the left (instead of from the left to the right).
        if is_master_prior_to_slave ^ (direction == self._WEB_GANTT_RESCHEDULE_BACKWARD):
            trigger_record = master_record
            related_record = slave_record
        else:
            trigger_record = slave_record
            related_record = master_record

        if not trigger_record._web_gantt_reschedule_is_record_candidate(start_date_field_name, stop_date_field_name):
            return {
                'type': 'warning',
                'message': _(
                    "You cannot move %(record)s towards %(related_record)s.",
                    record=trigger_record.name,
                    related_record=related_record.name,
                ),
            }

        with self.env.cr.savepoint() as sp:
            log_messages, old_vals_per_pill_id = trigger_record._web_gantt_action_reschedule_candidates(dependency_field_name, dependency_inverted_field_name, start_date_field_name, stop_date_field_name, direction, related_record)
            has_errors = bool(log_messages.get("errors"))
            sp.close(rollback=has_errors)
        notification_type = "success"
        message = _("Reschedule done successfully.")
        if has_errors or log_messages.get("warnings"):
            message = self._web_gantt_get_reschedule_message(log_messages)
            notification_type = "warning" if has_errors else "info"
        return {
            "type": notification_type,
            "message": message,
            "old_vals_per_pill_id": old_vals_per_pill_id,
        }

    def action_rollback_scheduling(self, old_vals_per_pill_id):
        for record in self:
            vals = old_vals_per_pill_id.get(str(record.id), old_vals_per_pill_id.get(record.id))
            if vals:
                record.write(vals)

    @api.model
    def _gantt_progress_bar(self, field, res_ids, start, stop):
        """ Get progress bar value per record.

            This method is meant to be overriden by each related model that want to
            implement this feature on Gantt groups. The progressbar is composed
            of a value and a max_value given for each groupedby field.

            Example:
                field = 'foo',
                res_ids = [1, 2]
                start_date = 01/01/2000, end_date = 01/07/2000,
                self = base()

            Result:
                {
                    1: {'value': 50, 'max_value': 100},
                    2: {'value': 25, 'max_value': 200},
                }

            :param string field: field on which there are progressbars
            :param list res_ids: res_ids of related records for which we need to compute progress bar
            :param string start_datetime: start date in utc
            :param string end_datetime: end date in utc
            :returns: dict of value and max_value per record
        """
        return {}

    @api.model
    def _gantt_unavailability(self, field, res_ids, start, stop, scale):
        """ Get unavailabilities data for a given set of resources.

        This method is meant to be overriden by each model that want to
        implement this feature on a Gantt view. A subslot is considered
        unavailable (and greyed) when totally covered by an unavailability.

        Example:
            * start = 01/01/2000 in datetime utc, stop = 01/07/2000 in datetime utc, scale = 'week',
              field = "empployee_id", res_ids = [3, 9]

            * The expected return value of this function is a dict of the form
                {
                    value: [{
                        start: <start date of first unavailabity in UTC format>,
                        stop: <stop date of first unavailabity in UTC format>
                    }, {
                        start: <start date of second unavailabity in UTC format>,
                        stop: <stop date of second unavailabity in UTC format>
                    }, ...]
                    ...
                }

              For example Marcel (3) is unavailable January 2 afternoon and
              January 4 the whole day, the dict should look like this
                {
                    3: [{
                        'start': '2018-01-02 14:00:00',
                        'stop': '2018-01-02 18:00:00'
                    }, {
                        'start': '2018-01-04 08:00:00',
                        'stop': '2018-01-04 18:00:00'
                    }]
                }
                Note that John (9) has no unavailabilies and thus 9 is not in
                returned dict

        :param string field: name of a many2X field
        :param list res_ids: list of values for field for which we want unavailabilities (a value is either False or an id)
        :param datetime start: start datetime
        :param datetime stop: stop datetime
        :param string scale: among "day", "week", "month" and "year"
        :returns: dict of unavailabilities
        """
        return {}

    def _web_gantt_get_candidates(self,
        dependency_field_name, dependency_inverted_field_name,
        start_date_field_name, stop_date_field_name,
        related_record, move_forward_without_conflicts,
    ):
        result = {
            'warnings': [],
            'errors': [],
        }
        # first get the children of self
        self_children_ids = []
        pills_to_plan_before = []
        pills_to_plan_after = []

        if move_forward_without_conflicts:
            candidates_to_exclude = {related_record.id}
        else:
            candidates_to_exclude = {self.id} | set(related_record[dependency_inverted_field_name].ids)

        if self._web_gantt_check_cycle_existance_and_get_rescheduling_candidates(
            self_children_ids, dependency_inverted_field_name,
            start_date_field_name, stop_date_field_name,
            candidates_to_exclude,
        ):
            result['errors'].append(self._WEB_GANTT_LOOP_ERROR)
            return (result, pills_to_plan_before, pills_to_plan_after, [])

        # second, get the ancestors of related_record
        related_record_ancestors_ids = []

        if move_forward_without_conflicts:
            candidates_to_exclude = {related_record.id} | set(self[dependency_field_name].ids)
        else:
            candidates_to_exclude = {self.id}

        if related_record._web_gantt_check_cycle_existance_and_get_rescheduling_candidates(
            related_record_ancestors_ids, dependency_field_name,
            start_date_field_name, stop_date_field_name,
            candidates_to_exclude,
        ):
            result['errors'].append(self._WEB_GANTT_LOOP_ERROR)
            return (result, pills_to_plan_before, pills_to_plan_after, [])

        # third, get the intersection between self children and related_record ancestors
        if move_forward_without_conflicts:
            all_pills_ids, pills_to_check_from_ids = self_children_ids, set(related_record_ancestors_ids)
        else:
            related_record_ancestors_ids.reverse()
            all_pills_ids, pills_to_check_from_ids = related_record_ancestors_ids, self_children_ids

        for pill_id in all_pills_ids:
            if pill_id in pills_to_check_from_ids:
                (pills_to_plan_before if move_forward_without_conflicts else pills_to_plan_after).append(pill_id)
            else:
                (pills_to_plan_after if move_forward_without_conflicts else pills_to_plan_before).append(pill_id)

        return (result, pills_to_plan_before, pills_to_plan_after, all_pills_ids)

    def _web_gantt_get_reschedule_message_per_key(self, key, params=None):
        if key == self._WEB_GANTT_LOOP_ERROR:
            return _("The dependencies are not valid, there is a cycle.")
        elif key == self._WEB_GANTT_NO_POSSIBLE_ACTION_ERROR:
            return _("There are no valid candidates to re-plan")
        elif key == "past_error":
            if params:  # params is the record that is in the past
                return _("%s cannot be scheduled in the past", params.display_name)
            else:
                return _("Impossible to schedule in the past.")
        else:
            return ""

    def _web_gantt_get_reschedule_message(self, log_messages):
        def get_messages(logs):
            messages = []
            for key in logs:
                message = self._web_gantt_get_reschedule_message_per_key(key, log_messages.get(key))
                if message:
                    messages.append(message)
            return messages

        messages = []
        errors = log_messages.get("errors")
        if errors:
            messages = get_messages(log_messages.get("errors"))
        else:
            messages = get_messages(log_messages.get("warnings", []))
        return "\n".join(messages)

    def _web_gantt_action_reschedule_candidates(
        self,
        dependency_field_name, dependency_inverted_field_name,
        start_date_field_name, stop_date_field_name,
        direction, related_record,
    ):
        """ Prepare the candidates according to the provided parameters and move them.

            :param dependency_field_name: The field name of the relation between the master and slave records.
            :param dependency_inverted_field_name: The field name of the relation between the slave and the parent
                   records.
            :param start_date_field_name: The start date field used in the gantt view.
            :param stop_date_field_name: The stop date field used in the gantt view.
            :param direction: The direction of the rescheduling 'forward' or 'backward'
            :param related_record: The record that self will be moving to
            :return: tuple(valid, message) (valid = True if Successful, message = None or contains the notification text if
                    text if valid = True or the error text if valid = False.
        """
        search_forward = direction == self._WEB_GANTT_RESCHEDULE_FORWARD
        # moving forward without conflicts
        if search_forward and self[stop_date_field_name] <= related_record[start_date_field_name] and related_record in self[dependency_inverted_field_name]:
            log_messages, pills_to_plan_before_related_record, pills_to_plan_after_related_record, all_candidates_ids = self._web_gantt_get_candidates(
                dependency_field_name, dependency_inverted_field_name,
                start_date_field_name, stop_date_field_name,
                related_record, True,
            )

            if log_messages.get("errors") or not pills_to_plan_before_related_record:
                return log_messages, {}

            # plan self_children backward from related_record
            pills_to_plan_before_related_record.reverse()
            log_messages, old_vals_per_pill_id = self._web_gantt_move_candidates(
                start_date_field_name, stop_date_field_name,
                dependency_field_name, dependency_inverted_field_name,
                False, pills_to_plan_before_related_record,
                related_record[start_date_field_name],
                all_candidates_ids, True,
            )

            if log_messages.get("errors") or not pills_to_plan_after_related_record:
                return log_messages, {} if log_messages.get("errors") else old_vals_per_pill_id

            # plan related_record_ancestors forward from related_record
            new_log_messages, second_old_vals_per_pill_id = self._web_gantt_move_candidates(
                start_date_field_name, stop_date_field_name,
                dependency_field_name, dependency_inverted_field_name,
                True, pills_to_plan_after_related_record,
                self[stop_date_field_name]
            )

            log_messages.setdefault("errors", []).extend(new_log_messages.get("errors", []))
            log_messages.setdefault("warnings", []).extend(new_log_messages.get("warnings", []))

            return log_messages, old_vals_per_pill_id | second_old_vals_per_pill_id
        # moving backward without conflicts
        elif related_record[stop_date_field_name] <= self[start_date_field_name] and related_record in self[dependency_field_name]:
            log_messages, pills_to_plan_before_related_record, pills_to_plan_after_related_record, all_candidates_ids = related_record._web_gantt_get_candidates(
                dependency_field_name, dependency_inverted_field_name,
                start_date_field_name, stop_date_field_name,
                self, False,
            )

            if log_messages.get("errors") or not pills_to_plan_after_related_record:
                return log_messages, {}

            # plan related_record_children_ids forward from related_record
            log_messages, old_vals_per_pill_id = self._web_gantt_move_candidates(
                start_date_field_name, stop_date_field_name,
                dependency_field_name, dependency_inverted_field_name,
                True, pills_to_plan_after_related_record,
                related_record[stop_date_field_name],
                all_candidates_ids, True,
            )

            if log_messages.get("errors") or not pills_to_plan_before_related_record:
                return log_messages, {} if log_messages.get("errors") else old_vals_per_pill_id

            # plan self_ancestors_ids backward from related_record
            pills_to_plan_before_related_record.reverse()
            new_log_messages, second_old_vals_per_pill_id = self._web_gantt_move_candidates(
                start_date_field_name, stop_date_field_name,
                dependency_field_name, dependency_inverted_field_name,
                False, pills_to_plan_before_related_record,
                self[start_date_field_name]
            )

            log_messages.setdefault("errors", []).extend(new_log_messages.get("errors", []))
            log_messages.setdefault("warnings", []).extend(new_log_messages.get("warnings", []))

            return log_messages, old_vals_per_pill_id | second_old_vals_per_pill_id
        # moving forward or backward with conflicts
        else:
            candidates_ids = []
            dependency = dependency_inverted_field_name if search_forward else dependency_field_name
            if self._web_gantt_check_cycle_existance_and_get_rescheduling_candidates(
                candidates_ids, dependency,
                start_date_field_name, stop_date_field_name,
            ):
                log_messages['errors'].append(self._WEB_GANTT_LOOP_ERROR)
                return {
                    "errors": [self._WEB_GANTT_LOOP_ERROR],
                }, {}

            if not candidates_ids:
                return {
                    "errors": [self._WEB_GANTT_NO_POSSIBLE_ACTION_ERROR],
                }, {}

            return self._web_gantt_move_candidates(
                start_date_field_name, stop_date_field_name,
                dependency_field_name, dependency_inverted_field_name,
                search_forward, candidates_ids,
                related_record[stop_date_field_name if search_forward else start_date_field_name]
            )

    def _web_gantt_is_candidate_in_conflict(self, start_date_field_name, stop_date_field_name, dependency_field_name, dependency_inverted_field_name):
        return (
            any(r[start_date_field_name] and r[stop_date_field_name] and self[start_date_field_name] < r[stop_date_field_name] for r in self[dependency_field_name])
            or any(r[start_date_field_name] and r[stop_date_field_name] and self[stop_date_field_name] > r[start_date_field_name] for r in self[dependency_inverted_field_name])
        )

    def _web_gantt_move_candidates(self, start_date_field_name, stop_date_field_name, dependency_field_name, dependency_inverted_field_name, search_forward, candidates_ids, date_candidate=None, all_candidates_ids=None, move_not_in_conflicts_candidates=False):
        """ Move candidates according to the provided parameters.

            :param start_date_field_name: The start date field used in the gantt view.
            :param stop_date_field_name: The stop date field used in the gantt view.
            :param dependency_field_name: The field name of the relation between the master and slave records.
            :param dependency_inverted_field_name: The field name of the relation between the slave and the parent
                   records.
            search_forward, candidates_ids, date_candidate
            :param search_forward: True if the direction = 'forward'
            :param candidates_ids: The candidates to reschdule
            :param date_candidate: The first possible date for the rescheduling
            :param all_candidates_ids: moving without conflicts is done in 2 steps, candidates_ids contains the candidates
                   to schedule during the step, and all_candidates_ids contains the candidates to schedule in the 2 steps
            :return: dict of list containing 2 keys, errors and warnings
        """
        result = {
            "errors": [],
            "warnings": [],
        }
        old_vals_per_pill_id = {}
        candidates = self.browse(candidates_ids)

        for i, candidate in enumerate(candidates):
            if not move_not_in_conflicts_candidates and not candidate._web_gantt_is_candidate_in_conflict(start_date_field_name, stop_date_field_name, dependency_field_name, dependency_inverted_field_name):
                continue

            start_date, end_date = candidate._web_gantt_reschedule_compute_dates(
                date_candidate,
                search_forward,
                start_date_field_name, stop_date_field_name
            )
            start_date, end_date = start_date.astimezone(timezone.utc), end_date.astimezone(timezone.utc)
            old_start_date, old_end_date = candidate[start_date_field_name], candidate[stop_date_field_name]
            if not candidate._web_gantt_reschedule_write_new_dates(
                start_date, end_date,
                start_date_field_name, stop_date_field_name
            ):
                result["errors"].append("past_error")
                result["past_error"] = candidate
                return result, {}
            else:
                old_vals_per_pill_id[candidate.id] = {
                    start_date_field_name: old_start_date,
                    stop_date_field_name: old_end_date,
                }

            if i + 1 < len(candidates):
                next_candidate = candidates[i + 1]
                if search_forward:
                    ancestors = next_candidate[dependency_field_name]
                    if ancestors:
                        date_candidate = max(ancestors.mapped(stop_date_field_name))
                    else:
                        date_candidate = end_date
                else:
                    children = next_candidate[dependency_inverted_field_name]
                    if children:
                        date_candidate = min(children.mapped(start_date_field_name))
                    else:
                        date_candidate = start_date

        return result, old_vals_per_pill_id

    def _web_gantt_check_cycle_existance_and_get_rescheduling_candidates(self,
        candidates_ids, dependency_field_name,
        start_date_field_name, stop_date_field_name,
        candidates_to_exclude=None, visited=None, ancestors=None,
    ):
        """ Get the current records' related records rescheduling candidates (explained in details
            in case 1 and case 2 in the below example)

            This method Executes a dfs (depth first search algorithm) on the dependencies tree to:
                1- detect cycles (detect if it's not a valid tree)
                2- return the topological sorting of the candidates to reschedule

            Example:

                                      [4]->[6]
                                            |
                                            v
                --->[0]->[1]->[2]     [5]->[7]->[8]-----------------
                |         |            |                           |
                |         v            v                           |
                |        [3]          [9]->[10]                    |
                |                                                  |
                ---------------------<x>----------------------------

                [0]->[1]: pill 0 should be done before 1
                <: left arrow to move pill 8 backward pill 0
                >: right arrow to move pill 0 forward pill 8
                x: delete the dependence

                Case 1:
                    If the right arrow is clicked, pill 0 should move forward. And as 1, 2, 3 are children of 0, they should be done after it,
                    they should also be moved forward.
                    This method will return False (no cycles) and a valid order of candidates = [0, 1, 2, 3] that should be scheduled

                Case 2:
                    If the left arrow is clicked, pill 8 should move backward task 0, as 4, 6, 5, 7 are ancestors for 8, they should be done
                    before it, they should be moved backward also. 9 and 10 should not be impacted as they are not ancestors of 8.
                    This method will return False (no cycles) and a valid order of candidates = [5, 4, 6, 7, 8] that should be scheduled

            Example 2:
                modify the previous tree by adding an edge from pill 2 to pill 0 (no more a tree after this added edge)
                 -----------
                 |         |
                 v         |
                [0]->[1]->[2]

                This method will return True because there is the cycle illustrated above

            :param candidates_ids: empty list that will contain the candidates at the end
            :param dependency_field_name: The field name of the relation between the master and slave records.
            :param dependency_inverted_field_name: The field name of the relation between the slave and the parent
                   records.
            :param start_date_field_name: The start date field used in the gantt view.
            :param stop_date_field_name: The stop date field used in the gantt view.
            :param candidates_to_exclude: candidates to exclude
            :param visited: set containing all the visited pills
            :param ancestors: set containing the visited ancestors for the current pill
            :return: bool, True if there is a cycle, else False.
                candidates_id will also contain the pills to plan in a valid topological order
        """
        if candidates_to_exclude is None:
            candidates_to_exclude = []
        if visited is None:
            visited = set()
        if ancestors is None:
            ancestors = []
        visited.add(self.id)
        ancestors.append(self.id)
        for child in self[dependency_field_name]:
            if child.id in ancestors:
                return True

            if child.id not in visited and child.id not in candidates_to_exclude and child._web_gantt_check_cycle_existance_and_get_rescheduling_candidates(candidates_ids, dependency_field_name, start_date_field_name, stop_date_field_name, candidates_to_exclude, visited, ancestors):
                return True

        ancestors.pop()
        if self._web_gantt_reschedule_is_record_candidate(start_date_field_name, stop_date_field_name) and self.id not in candidates_to_exclude:
            candidates_ids.insert(0, self.id)

        return False

    def _web_gantt_reschedule_compute_dates(
        self, date_candidate, search_forward, start_date_field_name, stop_date_field_name
    ):
        """ Compute start_date and end_date according to the provided arguments.
            This method is meant to be overridden when we need to add constraints that have to be taken into account
            in the computing of the start_date and end_date.

            :param date_candidate: The optimal date, which does not take any constraint into account.
            :param start_date_field_name: The start date field used in the gantt view.
            :param stop_date_field_name: The stop date field used in the gantt view.
            :return: a tuple of (start_date, end_date)
            :rtype: tuple(datetime, datetime)
        """
        search_factor = (1 if search_forward else -1)
        duration = search_factor * (self[stop_date_field_name] - self[start_date_field_name])
        return sorted([date_candidate, date_candidate + duration])

    @api.model
    def _web_gantt_reschedule_is_in_conflict(self, master, slave, start_date_field_name, stop_date_field_name):
        """ Get whether the dependency relation between a master and a slave record is in conflict.
            This check is By-passed for slave records if moving records forwards and the for
            master records if moving records backwards (see _web_gantt_get_rescheduling_candidates and
            _web_gantt_reschedule_is_in_conflict_or_force). In order to add condition that would not be
            by-passed, rather consider _web_gantt_reschedule_is_relation_candidate.

            :param master: The master record.
            :param slave: The slave record.
            :param start_date_field_name: The start date field used in the gantt view.
            :param stop_date_field_name: The stop date field used in the gantt view.
            :return: True if there is a conflict, False if not.
            :rtype: bool
        """
        return master[stop_date_field_name] > slave[start_date_field_name]

    @api.model
    def _web_gantt_reschedule_is_in_conflict_or_force(
            self, master, slave, start_date_field_name, stop_date_field_name, force
    ):
        """ Get whether the dependency relation between a master and a slave record is in conflict.
            This check is By-passed for slave records if moving records forwards and the for
            master records if moving records backwards. In order to add condition that would not be
            by-passed, rather consider _web_gantt_reschedule_is_relation_candidate.

            This def purpose is to be able to prevent the default behavior in some modules by overriding
            the def and forcing / preventing the rescheduling il all circumstances if needed.
            See _web_gantt_get_rescheduling_candidates.

            :param master: The master record.
            :param slave: The slave record.
            :param start_date_field_name: The start date field used in the gantt view.
            :param stop_date_field_name: The stop date field used in the gantt view.
            :param force: Force returning True
            :return: True if there is a conflict, False if not.
            :rtype: bool
        """
        return force or self._web_gantt_reschedule_is_in_conflict(
            master, slave, start_date_field_name, stop_date_field_name
        )

    def _web_gantt_reschedule_is_record_candidate(self, start_date_field_name, stop_date_field_name):
        """ Get whether the record is a candidate for the rescheduling. This method is meant to be overridden when
            we need to add a constraint in order to prevent some records to be rescheduled. This method focuses on the
            record itself (if you need to have information on the relation (master and slave) rather override
            _web_gantt_reschedule_is_relation_candidate).

            :param start_date_field_name: The start date field used in the gantt view.
            :param stop_date_field_name: The stop date field used in the gantt view.
            :return: True if record can be rescheduled, False if not.
            :rtype: bool
        """
        self.ensure_one()
        return self[start_date_field_name] and self[stop_date_field_name] \
            and self[start_date_field_name].replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)

    def _web_gantt_reschedule_is_relation_candidate(self, master, slave, start_date_field_name, stop_date_field_name):
        """ Get whether the relation between master and slave is a candidate for the rescheduling. This method is meant
            to be overridden when we need to add a constraint in order to prevent some records to be rescheduled.
            This method focuses on the relation between records (if your logic is rather on one record, rather override
            _web_gantt_reschedule_is_record_candidate).

            :param master: The master record we need to evaluate whether it is a candidate for rescheduling or not.
            :param slave: The slave record.
            :param start_date_field_name: The start date field used in the gantt view.
            :param stop_date_field_name: The stop date field used in the gantt view.
            :return: True if record can be rescheduled, False if not.
            :rtype: bool
        """
        return True

    def _web_gantt_reschedule_write_new_dates(
        self, new_start_date, new_stop_date, start_date_field_name, stop_date_field_name
    ):
        """ Write the dates values if new_start_date is in the future.

            :param new_start_date: The start_date to write.
            :param new_stop_date: The stop_date to write.
            :param start_date_field_name: The start date field used in the gantt view.
            :param stop_date_field_name: The stop date field used in the gantt view.
            :return: True if successful, False if not.
            :rtype: bool

            epsilon = 30 seconds was added because the first valid interval can be now and because of some seconds, it will become < now() at the comparaison moment
            it's a matter of some seconds
        """
        new_start_date = new_start_date.astimezone(timezone.utc).replace(tzinfo=None)
        if new_start_date < datetime.now() + timedelta(seconds=-30):
            return False

        self.write({
            start_date_field_name: new_start_date,
            stop_date_field_name: new_stop_date.astimezone(timezone.utc).replace(tzinfo=None)
        })
        return True
