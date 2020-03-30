# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class SequenceMixin(models.AbstractModel):
    """Mechanism used to have an editable sequence number.

    Be careful of how you use this regarding the prefixes. More info in the
    docstring of _get_last_sequence.
    """

    _name = 'sequence.mixin'
    _description = "Automatic sequence"

    _sequence_field = "name"
    _sequence_monthly_regex = r'^(?P<prefix1>.*?)(?P<year>\d{4})(?P<prefix2>\D*?)(?P<month>\d{2})(?P<prefix3>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$'
    _sequence_yearly_regex = r'^(?P<prefix1>.*?)(?P<year>\d{4})(?P<prefix2>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$'
    _sequence_fixed_regex = r'^(?P<prefix1>.*?)(?P<seq>\d*)(?P<suffix>\D*?)$'

    @api.model
    def _deduce_sequence_number_reset(self, name):
        """Detect if the used sequence resets yearly, montly or never.

        :param name: the sequence that is used as a reference to detect the resetting
            periodicity. Typically, it is the last before the one you want to give a
            sequence.
        """
        def _check_grouping(grouping, optional=None, required=None):
            sequence_dict = sequence.groupdict()
            return all(key in sequence_dict for key in (optional or [])) and all(sequence_dict.get(key) for key in (required or []))

        if not name:
            return False
        sequence = re.match(self._sequence_monthly_regex, name)
        if sequence and _check_grouping(sequence, ['prefix1', 'prefix2', 'prefix3', 'seq', 'suffix'], ['year', 'month']) and 2000 <= int(sequence.group('year')) <= 2100 and 0 < int(sequence.group('month')) <= 12:
            return 'month'
        sequence = re.match(self._sequence_yearly_regex, name)
        if sequence and _check_grouping(sequence, ['prefix1', 'prefix2', 'seq', 'suffix'], ['year']) and 2000 <= int(sequence.group('year')) <= 2100:
            return 'year'
        sequence = re.match(self._sequence_fixed_regex, name)
        if sequence and _check_grouping(sequence, ['prefix1', 'seq', 'suffix']):
            return 'never'
        raise ValidationError(_('The sequence regex should at least contain the prefix1, seq and suffix grouping keys. For instance:\n^(?P<prefix1>.*?)(?P<seq>\d*)(?P<suffix>\D*?)$'))

    def _get_last_sequence_domain(self, relaxed=False):
        """Get the sql domain to retreive the previous sequence number.

        This function should be overriden by models heriting from this mixin.

        :param relaxed: see _get_last_sequence.

        :returns: tuple(where_string, where_params): with
            where_string: the entire SQL WHERE clause as a string.
            where_params: a dictionary containing the parameters to substitute
                at the execution of the query.
        """
        self.ensure_one()
        return "", {}

    def _get_starting_sequence(self):
        """Get a default sequence number.

        This function should be overriden by models heriting from this mixin
        This number will be incremented so you probably want to start the sequence at 0.

        :return: string to use as the default sequence to increment
        """
        self.ensure_one()
        return "00000000"

    def _get_highest_query(self):
        return "SELECT {field} FROM {table} {where_string} ORDER BY {field} DESC LIMIT 1 FOR UPDATE"

    def _get_last_sequence(self, relaxed=False):
        """Retrieve the previous sequence.

        This is done by taking the number with the greatest alphabetical value within
        the domain of _get_last_sequence_domain. This means that the prefix has a
        huge importance.
        For instance, if you have INV/2019/0001 and INV/2019/0002, when you rename the
        last one to FACT/2019/0001, one might expect the next number to be
        FACT/2019/0002 but it will be INV/2019/0002 (again) because INV > FACT.
        Therefore, changing the prefix might not be convenient during a period, and
        would only work when the numbering makes a new start (domain returns by
        _get_last_sequence_domain is [], i.e: a new year).

        :param field_name: the field that contains the sequence.
        :param relaxed: this should be set to True when a previous request didn't find
            something without. This allows to find a pattern from a previous period, and
            try to adapt it for the new period.

        :return: the string of the previous sequence or None if there wasn't any.
        """
        self.ensure_one()
        if self._sequence_field not in self._fields or not self._fields[self._sequence_field].store:
            raise ValidationError(_('%s is not a stored field') % self._sequence_field)
        where_string, param = self._get_last_sequence_domain(relaxed)
        if self.id or self.id.origin:
            where_string += " AND id != %(id)s "
            param['id'] = self.id or self.id.origin

        query = self._get_highest_query().format(table=self._table, where_string=where_string, field=self._sequence_field)

        self.flush([self._sequence_field])
        self.env.cr.execute(query, param)
        return (self.env.cr.fetchone() or [None])[0]

    def _set_next_sequence(self):
        """Set the next sequence.

        This method ensures that the field is set both in the ORM and in the database.
        This is necessary because we use a database query to get the previous sequence,
        and we need that query to always be executed on the latest data.

        :param field_name: the field that contains the sequence.
        """
        self.ensure_one()
        last_sequence = self._get_last_sequence() or self._get_starting_sequence()

        sequence = re.match(self._sequence_fixed_regex, last_sequence)
        value = ("{prefix}{seq:0%sd}{suffix}" % len(sequence.group('seq'))).format(
            prefix=sequence.group('prefix1'),
            seq=int(sequence.group('seq') or 0) + 1,
            suffix=sequence.group('suffix'),
        )
        self[self._sequence_field] = value
        self.flush([self._sequence_field])
