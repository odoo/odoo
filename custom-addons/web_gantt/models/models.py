# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import datetime, timezone
from lxml.builder import E

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.misc import OrderedSet, unique


class Base(models.AbstractModel):
    _inherit = 'base'

    _start_name = 'date_start'       # start field to use for default gantt view
    _stop_name = 'date_stop'         # stop field to use for default gantt view

    # action_gantt_reschedule utils
    _WEB_GANTT_RESCHEDULE_FORWARD = 'forward'
    _WEB_GANTT_RESCHEDULE_BACKWARD = 'backward'
    _WEB_GANTT_LOOP_ERROR = 'loop_error'

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
    def get_gantt_data(
        self, domain, groupby, read_specification, limit=None, offset=0,
    ):
        """
        Returns the result of a read_group (and optionally search for and read records inside each
        group), and the total number of groups matching the search domain.

        :param domain: search domain
        :param groupby: list of field to group on (see ``groupby``` param of ``read_group``)
        :param read_specification: web_read specification to read records within the groups
        :param limit: see ``limit`` param of ``read_group``
        :param offset: see ``offset`` param of ``read_group``
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
        all_records = self.search_fetch([('id', 'in', all_record_ids)], read_specification.keys())
        final_result['records'] = all_records.web_read(read_specification)

        ordered_set_ids = OrderedSet(all_records._ids)
        for group in final_result['groups']:
            # Reorder __record_ids
            group['__record_ids'] = list(ordered_set_ids & OrderedSet(group['__record_ids']))
            # We don't need these in the gantt view
            del group['__domain']
            del group[f'{groupby[0]}_count' if lazy else '__count']
            group.pop('__fold', None)

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
            :return: True if Successful, a client action of notification type if not.
        """

        if direction not in (self._WEB_GANTT_RESCHEDULE_FORWARD, self._WEB_GANTT_RESCHEDULE_BACKWARD):
            raise ValueError("Invalid direction %r" % direction)

        master_record, slave_record = self.env[self._name].browse([master_record_id, slave_record_id])

        search_domain = [(dependency_field_name, 'in', master_record.id), ('id', '=', slave_record.id)]
        if not self.env[self._name].search(search_domain, limit=1):
            raise ValueError("Record '%r' is not a parent record of '%r'" % (master_record.name, slave_record.name))

        if not self._web_web_gantt_reschedule_is_relation_candidate(
                master_record, slave_record, start_date_field_name, stop_date_field_name):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _('You cannot reschedule %s towards %s.',
                                 master_record.name, slave_record.name),
                }
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

        cache = self._web_gantt_reschedule_get_empty_cache()

        new_start_date, new_stop_date = trigger_record._web_gantt_reschedule_record(
            related_record, related_record == master_record,
            start_date_field_name, stop_date_field_name,
            cache
        )

        result = trigger_record._web_gantt_reschedule_write_new_dates(
            new_start_date, new_stop_date, start_date_field_name, stop_date_field_name,
        )

        sp = self.env.cr.savepoint()

        record_ids_to_exclude = defaultdict(list)

        result = result is True and trigger_record._web_gantt_action_reschedule_related_records(
            dependency_field_name, dependency_inverted_field_name,
            start_date_field_name, stop_date_field_name,
            direction,
            record_ids_to_exclude,
            cache
        )

        if result is not True:
            if result is False:
                notification_type = 'warning'
                message = _('Records that are in the past cannot be automatically rescheduled. They should be manually rescheduled instead.')
            elif result == self._WEB_GANTT_LOOP_ERROR:
                notification_type = 'info'
                message = _('You cannot reschedule tasks that do not follow a direct dependency path. '
                            'Only the first task has been automatically rescheduled.')
            else:
                raise ValueError('Unsupported result value')
            result = {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': notification_type,
                        'message': message,
                    }
                }

        sp.close(rollback=result is not True)
        return result

    @api.model
    def gantt_progress_bar(self, fields, res_ids, date_start_str, date_stop_str):
        """ Get progress bar value per record.

            This method is meant to be overriden by each related model that want to
            implement this feature on Gantt groups. The progressbar is composed
            of a value and a max_value given for each groupedby field.

            Example:
                fields = ['foo', 'bar'],
                res_ids = {'foo': [1, 2], 'bar':[2, 3]}
                start_date = 01/01/2000, end_date = 01/07/2000,
                self = base()

            Result:
                {
                    'foo': {
                        1: {'value': 50, 'max_value': 100},
                        2: {'value': 25, 'max_value': 200},
                    },
                    'bar': {
                        2: {'value': 65, 'max_value': 85},
                        3: {'value': 30, 'max_value': 95},
                    }
                }

            :param list fields: fields on which there are progressbars
            :param dict res_ids: res_ids of related records for which we need to compute progress bar
            :param string date_start_str: start date
            :param string date_stop_str: stop date
            :returns: dict of value and max_value per record
        """
        return {}

    @api.model
    def gantt_unavailability(self, start_date, end_date, scale, group_bys=None, rows=None):
        """ Get unavailabilities data to display in the Gantt view.

        This method is meant to be overriden by each model that want to
        implement this feature on a Gantt view. A subslot is considered
        unavailable (and greyed) when totally covered by an unavailability.

        Example:
            * start_date = 01/01/2000, end_date = 01/07/2000, scale = 'week',
              rows = [{
                groupedBy: ["project_id", "user_id", "stage_id"],
                resId: 8,
                rows: [{
                    groupedBy: ["user_id", "stage_id"],
                    resId: 18,
                    rows: [{
                        groupedBy: ["stage_id"],
                        resId: 3,
                        rows: []
                    }, {
                        groupedBy: ["stage_id"],
                        resId: 9,
                        rows: []
                    }]
                }, {
                    groupedBy: ["user_id", "stage_id"],
                    resId: 22,
                    rows: [{
                        groupedBy: ["stage_id"],
                        resId: 9,
                        rows: []
                    }]
                }]
            }, {
                groupedBy: ["project_id", "user_id", "stage_id"],
                resId: 9,
                rows: [{
                    groupedBy: ["user_id", "stage_id"],
                    resId: None,
                    rows: [{
                        groupedBy: ["stage_id"],
                        resId: 3,
                        rows: []
                    }]
            }, {
                groupedBy: ["project_id", "user_id", "stage_id"],
                resId: 27,
                rows: []
            }]

            * The expected return value of this function is the rows dict with
              a new 'unavailabilities' key in each row for which you want to
              display unavailabilities. Unavailablitities is a list
              (naturally ordered and pairwise disjoint) in the form:
              [{
                  start: <start date of first unavailabity in UTC format>,
                  stop: <stop date of first unavailabity in UTC format>
              }, {
                  start: <start date of second unavailabity in UTC format>,
                  stop: <stop date of second unavailabity in UTC format>
              }, ...]

              To display that Marcel is unavailable January 2 afternoon and
              January 4 the whole day in his To Do row, this particular row in
              the rows dict should look like this when returning the dict at the
              end of this function :
              { ...
                {
                    groupedBy: ["stage_id"],
                    resId: 3,
                    rows: []
                    unavailabilities: [{
                        'start': '2018-01-02 14:00:00',
                        'stop': '2018-01-02 18:00:00'
                    }, {
                        'start': '2018-01-04 08:00:00',
                        'stop': '2018-01-04 18:00:00'
                    }]
                }
                ...
              }



        :param datetime start_date: start date
        :param datetime stop_date: stop date
        :param string scale: among "day", "week", "month" and "year"
        :param None | list[str] group_bys: group_by fields
        :param dict rows: dict describing the current rows of the gantt view
        :returns: dict of unavailability
        """
        return rows

    def _web_gantt_action_reschedule_related_records(
        self,
        dependency_field_name, dependency_inverted_field_name,
        start_date_field_name, stop_date_field_name,
        direction,
        record_ids_to_exclude,
        cache
    ):
        """ Reschedule the related records, that is the records available in both fields dependency_field_name and
            dependency_inverted_field_name and which satisfies some conditions which are tested in
            _web_gantt_get_rescheduling_candidates

            :param dependency_field_name: The field name of the relation between the master and slave records.
            :param dependency_inverted_field_name: The field name of the relation between the slave and the parent
                   records.
            :param start_date_field_name: The start date field used in the gantt view.
            :param stop_date_field_name: The stop date field used in the gantt view.
            :param direction: The direction of the rescheduling 'forward' or 'backward'
            :param record_ids_to_exclude: The record Ids that have to be excluded from the return candidates.
            :param cache: An object that contains reusable information in the context of gantt record rescheduling.
            :return: True if successful, False if not.
            :rtype: bool
        """
        rescheduling_candidates = self._web_gantt_get_rescheduling_candidates(
            dependency_field_name, dependency_inverted_field_name,
            start_date_field_name, stop_date_field_name,
            direction,
            record_ids_to_exclude
        )

        if rescheduling_candidates is False:
            return self._WEB_GANTT_LOOP_ERROR

        if not rescheduling_candidates:
            return True

        result = True
        records_to_propagate = self.env[self._name]
        for rescheduling_candidate in rescheduling_candidates:
            record, related_record, is_related_record_master = rescheduling_candidate

            new_start_date, new_stop_date = record._web_gantt_reschedule_record(
                related_record, is_related_record_master,
                start_date_field_name, stop_date_field_name,
                cache
            )
            record_write_result = record._web_gantt_reschedule_write_new_dates(
                new_start_date, new_stop_date,
                start_date_field_name, stop_date_field_name,
            )

            if record_write_result:
                records_to_propagate |= record
                record_ids_to_exclude[record.id] = record_ids_to_exclude[related_record.id] + [related_record.id]

            result &= record_write_result

        for record in self:
            record_ids_to_exclude.pop(record.id, None)

        related_records_result = records_to_propagate._web_gantt_action_reschedule_related_records(
            dependency_field_name, dependency_inverted_field_name,
            start_date_field_name, stop_date_field_name,
            direction,
            record_ids_to_exclude,
            cache
        )
        if isinstance(related_records_result, bool):
            result &= related_records_result
        else:
            result = related_records_result

        return result

    def _web_gantt_get_rescheduling_candidates(
        self,
        dependency_field_name, dependency_inverted_field_name,
        start_date_field_name, stop_date_field_name,
        direction,
        record_ids_to_exclude
    ):
        """ Get the current records' related records rescheduling candidates (the records that depend on them as well
            as the records they depend on) for the rescheduling process as well as their reference records (the
            furthest record that depends on it, as well as the furthest record it depends on).

            :param dependency_field_name: The field name of the relation between the master and slave records.
            :param dependency_inverted_field_name: The field name of the relation between the slave and the parent
                   records.
            :param start_date_field_name: The start date field used in the gantt view.
            :param stop_date_field_name: The stop date field used in the gantt view.
            :param direction: The direction of the rescheduling 'forward' or 'backward'
            :param record_ids_to_exclude: The record Ids that have to be excluded from the return candidates.
            :return: a list of tuples (record, related_record, is_related_record_master)
                     where: - record is the record to be rescheduled
                            - related_record is the record that is the target of the rescheduling
                            - is_related_record_master informs whether the related_record is a record that the current
                              record depends on (so-called master) or a record that depends on the current record
                              (so-called slave)
            :rtype: tuple(AbstractModel, AbstractModel, bool)
        """
        rescheduling_forward = direction == self._WEB_GANTT_RESCHEDULE_FORWARD
        rescheduling_backward = direction == self._WEB_GANTT_RESCHEDULE_BACKWARD

        slave_per_record = defaultdict(lambda: self.env[self._name])
        master_per_record = defaultdict(lambda: self.env[self._name])
        records_to_reschedule = self.env[self._name]

        # The goal is to automatically exclude ids from the `dependency_field_name` and `dependency_inverted_field_name`
        # fields but not the self.ids. And the later call on _web_gantt_reschedule_is_record_candidate will ensure that
        # the self.ids are good candidates.

        for record in self:
            if record.id in record_ids_to_exclude[record.id] \
               or not record._web_gantt_reschedule_is_record_candidate(start_date_field_name, stop_date_field_name):
                continue
            for master_record in record[dependency_field_name]:
                #
                # A      B       C      D
                #   \      \   /      /
                #     ------ F ------
                #          /   \
                #    G ---       --- H
                #
                # So if we are considering we are rescheduling F towards G then, once F is moved, B will be
                # added to the candidates as it will be assessed as being in conflict with F, but A won't.
                #
                # So if we are considering we are rescheduling F towards H then, once F is moved, A, B and G
                # will be added to the candidates as we are rescheduling forward.

                if master_record.id in record_ids_to_exclude[record.id] \
                   or not master_record._web_gantt_reschedule_is_record_candidate(
                        start_date_field_name, stop_date_field_name) \
                   or not self._web_web_gantt_reschedule_is_relation_candidate(
                        master_record, record, start_date_field_name, stop_date_field_name) \
                   or not self._web_gantt_reschedule_is_in_conflict_or_force(
                            master_record, record, start_date_field_name, stop_date_field_name, rescheduling_forward):
                    continue

                # If we have two same candidates, it means that we are resolving a `loop`
                # with an even number of members.
                if master_record in slave_per_record:
                    return False

                slave_per_record[master_record] = record
                records_to_reschedule |= master_record

            for slave_record in record[dependency_inverted_field_name]:
                #
                # A      B       C      D
                #   \      \   /      /
                #     ------ F ------
                #          /   \
                #    G ---       --- H
                #
                # So if we are considering we are rescheduling F towards H then, once F is moved, C will be
                # added to the candidates as it will be assessed as being in conflict with F, but D won't.
                #
                # So if we are considering we are rescheduling F towards G then C, once F is moved, D and H
                # will be added to the candidates as we are rescheduling backward.

                if slave_record.id in record_ids_to_exclude[record.id] \
                   or not slave_record._web_gantt_reschedule_is_record_candidate(
                        start_date_field_name, stop_date_field_name) \
                   or not self._web_web_gantt_reschedule_is_relation_candidate(
                        record, slave_record, start_date_field_name, stop_date_field_name) \
                   or not self._web_gantt_reschedule_is_in_conflict_or_force(
                            record, slave_record, start_date_field_name, stop_date_field_name, rescheduling_backward):
                    continue

                # If we have two same candidates, it means that we are resolving a `loop`
                # with an even number of members.
                if slave_record in master_per_record:
                    return False

                master_per_record[slave_record] = record
                records_to_reschedule |= slave_record

        # If we have a record that is both a slave and a master candidate, it means that we are resolving a `loop`
        # with an even number of members.
        if set.intersection(set(slave_per_record.keys()), set(master_per_record.keys())):
            if set.intersection(*map(set, [record_ids_to_exclude[rec.id]for rec in self])):
                return False

        # If we have a record from self that is a slave candidate and a record from self that is a master candidate,
        # it means that we are resolving a loop with an odd number of members.
        if any(record in slave_per_record.keys() for record in self) and \
           any(record in master_per_record.keys() for record in self):
            return False

        return [
            (record_to_reschedule,
             slave_per_record[record_to_reschedule] or master_per_record[record_to_reschedule],
             bool(master_per_record[record_to_reschedule])
             ) for record_to_reschedule in records_to_reschedule
        ]

    def _web_gantt_reschedule_compute_dates(
        self, date_candidate, search_forward, start_date_field_name, stop_date_field_name, cache
    ):
        """ Compute start_date and end_date according to the provided arguments.
            This method is meant to be overridden when we need to add constraints that have to be taken into account
            in the computing of the start_date and end_date.

            :param date_candidate: The optimal date, which does not take any constraint into account.
            :param start_date_field_name: The start date field used in the gantt view.
            :param stop_date_field_name: The stop date field used in the gantt view.
            :param cache: An object that contains reusable information in the context of gantt record rescheduling.
            :return: a tuple of (start_date, end_date)
            :rtype: tuple(datetime, datetime)
        """
        search_factor = (1 if search_forward else -1)
        duration = search_factor * (self[stop_date_field_name] - self[start_date_field_name])
        return sorted([date_candidate, date_candidate + duration])

    @api.model
    def _web_gantt_reschedule_get_empty_cache(self):
        """ Get an empty object that would be used in order to prevent successive database calls during the
            rescheduling process.

            :return: An object that contains reusable information in the context of gantt record rescheduling.
            :rtype: dict
        """
        return {}

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

    @api.model
    def _web_web_gantt_reschedule_is_relation_candidate(self, master, slave, start_date_field_name, stop_date_field_name):
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

    def _web_gantt_reschedule_record(
        self, related_record, is_related_record_master, start_date_field_name, stop_date_field_name, cache
    ):
        """ Shift the record in the future or the past according to the passed arguments.

            :param related_record: The related record (either the master or slave record).
            :param is_related_record_master: Tells whether the related record is the master or slave in the dependency.
            :param start_date_field_name: The start date field used in the gantt view.
            :param stop_date_field_name: The stop date field used in the gantt view.
            :param cache: An object that contains reusable information in the context of gantt record rescheduling.
            :return: a tuple of (start_date, end_date)
            :rtype: tuple(datetime, datetime)
        """
        self.ensure_one()
        # If the related_record is the master, then we look for a date after the value of its stop_date_field_name.
        # If the related_record is the slave, then we look for a date prior to the value of its start_date_field_name.
        search_forward = is_related_record_master
        if search_forward:
            date_candidate = related_record[stop_date_field_name].replace(tzinfo=timezone.utc)
        else:
            date_candidate = related_record[start_date_field_name].replace(tzinfo=timezone.utc)

        return self.sudo()._web_gantt_reschedule_compute_dates(
            date_candidate,
            search_forward,
            start_date_field_name, stop_date_field_name,
            cache
        )

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
        """
        if new_start_date < datetime.now(timezone.utc):
            return False

        self.write({
            start_date_field_name: new_start_date.astimezone(timezone.utc).replace(tzinfo=None),
            stop_date_field_name: new_stop_date.astimezone(timezone.utc).replace(tzinfo=None)
        })
        return True
