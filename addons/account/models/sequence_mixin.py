# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.account.exceptions import SequenceMixinValidationError

import re
from psycopg2 import sql
from collections import defaultdict


class SequenceMixin(models.AbstractModel):
    """Mechanism used to have an editable sequence number."""

    _name = 'sequence.mixin'
    _description = "Automatic sequence"

    _sequence_field = "name"
    _sequence_date_field = "date"
    _sequence_index = False
    _sequence_monthly_regex = r'^(?P<prefix1>.*?)(?P<year>((?<=\D)|(?<=^))(\d{4}|(\d{2}(?=\D))))(?P<prefix2>\D*?)(?P<month>\d{2})(?P<prefix3>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$'
    _sequence_yearly_regex = r'^(?P<prefix1>.*?)(?P<year>((?<=\D)|(?<=^))(\d{4}|\d{2}))(?P<prefix2>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$'
    _sequence_fixed_regex = r'^(?P<prefix1>.*?)(?P<seq>\d{0,9})(?P<suffix>\D*?)$'

    sequence_prefix = fields.Char(compute='_compute_split_sequence', store=True)
    sequence_number = fields.Integer(compute='_compute_split_sequence', store=True)

    def init(self):
        # Add an index to optimise the query searching for the highest sequence number
        if not self._abstract and self._sequence_index:
            index_name = self._table + '_sequence_index'
            self.env.cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', (index_name,))
            if not self.env.cr.fetchone():
                self.env.cr.execute(sql.SQL("""
                    CREATE INDEX {index_name} ON {table} ({sequence_index}, sequence_prefix desc, sequence_number desc, {field});
                    CREATE INDEX {index2_name} ON {table} ({sequence_index}, id desc, sequence_prefix);
                """).format(
                    sequence_index=sql.Identifier(self._sequence_index),
                    index_name=sql.Identifier(index_name),
                    index2_name=sql.Identifier(index_name + "2"),
                    table=sql.Identifier(self._table),
                    field=sql.Identifier(self._sequence_field),
                ))

    def __init__(self, pool, cr):
        api.constrains(self._sequence_field, self._sequence_date_field)(type(self)._constrains_date_sequence)
        return super().__init__(pool, cr)

    def _constrains_date_sequence(self):
        # Make it possible to bypass the constraint to allow edition of already messed up documents.
        # /!\ Do not use this to completely disable the constraint as it will make this mixin unreliable.
        constraint_date = fields.Date.to_date(self.env['ir.config_parameter'].sudo().get_param(
            'sequence.mixin.constraint_start_date',
            '1970-01-01'
        ))
        failed = self.env[self._name]
        for record in self:
            date = fields.Date.to_date(record[record._sequence_date_field])
            sequence = record[record._sequence_field]
            if sequence and date and date > constraint_date:
                format_values = record._get_sequence_format_param(sequence)[1]
                if (
                    format_values['year'] and format_values['year'] != date.year % 10**len(str(format_values['year']))
                    or format_values['month'] and format_values['month'] != date.month
                ):
                    failed += record
        if failed:
            raise SequenceMixinValidationError(failed)

    @api.depends(lambda self: [self._sequence_field])
    def _compute_split_sequence(self):
        for record in self:
            sequence = record[record._sequence_field] or ''
            regex = re.sub(r"\?P<\w+>", "?:", record._sequence_fixed_regex.replace(r"?P<seq>", ""))  # make the seq the only matching group
            matching = re.match(regex, sequence)
            record.sequence_prefix = sequence[:matching.start(1)]
            record.sequence_number = int(matching.group(1) or 0)

    @api.model
    def _deduce_sequence_number_reset(self, name):
        """Detect if the used sequence resets yearly, montly or never.

        :param name: the sequence that is used as a reference to detect the resetting
            periodicity. Typically, it is the last before the one you want to give a
            sequence.
        """
        def _check_grouping(grouping, required):
            sequence_dict = grouping.groupdict()
            if 'seq' not in sequence_dict or any(not sequence_dict.get(key) for key in required):
                return False
            if 'year' in required and not (
                2000 <= int(sequence_dict.get('year') or -1) <= 2100
                or len(sequence_dict.get('year') or '') == 2
            ):
                return False
            if 'month' in required and not 1 <= int(sequence_dict.get('month') or -1) <= 12:
                return False
            return True

        if not name:
            return False
        sequence = re.match(self._sequence_monthly_regex, name)
        if sequence and _check_grouping(sequence, ['year', 'month']):
            return 'month'
        sequence = re.match(self._sequence_yearly_regex, name)
        if sequence and _check_grouping(sequence, ['year']):
            return 'year'
        sequence = re.match(self._sequence_fixed_regex, name)
        if sequence and _check_grouping(sequence, []):
            return 'never'
        raise ValidationError(_(
            'The sequence regex should at least contain the seq grouping keys. For instance:\n'
            '^(?P<prefix1>.*?)(?P<seq>\d*)(?P<suffix>\D*?)$'
        ))

    def _get_last_sequence_domain(self, relaxed=False):
        """Get the sql domain to retreive the previous sequence number.

        This function should be overriden by models inheriting from this mixin.

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

    def _get_last_sequence(self, relaxed=False):
        """Retrieve the previous sequence.

        First we look at the last (with the highest `id`) prefix used for the domain defined.
        Then we take the highest number with the same prefix in the samme domain defined.
        This will lock the row with the highest number, preventing giving two sequences at the same
        time.

        :param field_name: the field that contains the sequence.
        :param relaxed: this should be set to True when a previous request didn't find
            something without. This allows to find a pattern from a previous period, and
            try to adapt it for the new period.

        :return: the string of the previous sequence or None if there wasn't any.
        """
        self.ensure_one()
        if self._sequence_field not in self._fields or not self._fields[self._sequence_field].store:
            raise ValidationError(_('%s is not a stored field', self._sequence_field))
        where_string, param = self._get_last_sequence_domain(relaxed)
        if self.id or self.id.origin:
            where_string += " AND id != %(id)s "
            param['id'] = self.id or self.id.origin

        query = """
            UPDATE {table} SET write_date = write_date WHERE id = (
                SELECT id FROM {table}
                {where_string}
                AND sequence_prefix = (SELECT sequence_prefix FROM {table} {where_string} ORDER BY id DESC LIMIT 1)
                ORDER BY sequence_number DESC
                LIMIT 1
            )
            RETURNING {field};
        """.format(
            table=self._table,
            where_string=where_string,
            field=self._sequence_field,
        )

        self.flush([self._sequence_field, 'sequence_number', 'sequence_prefix'])
        self.env.cr.execute(query, param)
        return (self.env.cr.fetchone() or [None])[0]

    def _get_sequence_format_param(self, previous):
        """Get the python format and format values for the sequence.

        :param previous: the sequence we want to extract the format from
        :return tuple(format, format_values):
            format is the format string on which we should call .format()
            format_values is the dict of values to format the `format` string
            ``format.format(**format_values)`` should be equal to ``previous``
        """
        sequence_number_reset = self._deduce_sequence_number_reset(previous)
        regex = self._sequence_fixed_regex
        if sequence_number_reset == 'year':
            regex = self._sequence_yearly_regex
        elif sequence_number_reset == 'month':
            regex = self._sequence_monthly_regex

        format_values = re.match(regex, previous).groupdict()
        format_values['seq_length'] = len(format_values['seq'])
        format_values['year_length'] = len(format_values.get('year', ''))
        if not format_values.get('seq') and 'prefix1' in format_values and 'suffix' in format_values:
            # if we don't have a seq, consider we only have a prefix and not a suffix
            format_values['prefix1'] = format_values['suffix']
            format_values['suffix'] = ''
        for field in ('seq', 'year', 'month'):
            format_values[field] = int(format_values.get(field) or 0)

        placeholders = re.findall(r'(prefix\d|seq|suffix\d?|year|month)', regex)
        format = ''.join(
            "{seq:0{seq_length}d}" if s == 'seq' else
            "{month:02d}" if s == 'month' else
            "{year:0{year_length}d}" if s == 'year' else
            "{%s}" % s
            for s in placeholders
        )
        return format, format_values

    def _set_next_sequence(self):
        """Set the next sequence.

        This method ensures that the field is set both in the ORM and in the database.
        This is necessary because we use a database query to get the previous sequence,
        and we need that query to always be executed on the latest data.

        :param field_name: the field that contains the sequence.
        """
        self.ensure_one()
        last_sequence = self._get_last_sequence()
        new = not last_sequence
        if new:
            last_sequence = self._get_last_sequence(relaxed=True) or self._get_starting_sequence()

        format, format_values = self._get_sequence_format_param(last_sequence)
        if new:
            format_values['seq'] = 0
            format_values['year'] = self[self._sequence_date_field].year % (10 ** format_values['year_length'])
            format_values['month'] = self[self._sequence_date_field].month
        format_values['seq'] = format_values['seq'] + 1

        self[self._sequence_field] = format.format(**format_values)
        self._compute_split_sequence()

    def _set_next_sequence_batch(self, grouping_key, date_key=None, order_key=None):
        """Set the next sequence on multiple documents at once.

        The method `_set_next_sequence` is quite slow because it has to perform multiple SQL
        queries. This method reduces that by doing one query per group/date.
        :param grouping_key (function<Model,Any>): key used to dispatch the records in different
            batches.
        :param date_key (function<Model,Any>): key used to dispatch the batches in different date
            zones. Date zones that have the same format will be regroupped before assigning the
            sequence number.
        """
        if date_key is None:
            def date_key(record):
                date = record[record._sequence_date_field]
                return (date.year, date.month)

        if order_key is None:
            def order_key(record):
                return (record[record._sequence_date_field], record.id)

        grouped = defaultdict(  # key: grouping_key
            lambda: defaultdict(  # key: date_key
                lambda: {
                    'records': self.env[self._name],
                    'format': False,
                    'format_values': False,
                    'reset': False
                }
            )
        )
        for record in self.sorted(order_key):
            group = grouped[grouping_key(record)][date_key(record)]
            if not group['records']:
                # Compute all the values needed to sequence this whole group
                record._set_next_sequence()
                seq = record[record._sequence_field]
                group['format'], group['format_values'] = record._get_sequence_format_param(seq)
                group['reset'] = record._deduce_sequence_number_reset(seq)
            group['records'] += record

        # Merge the groups depending on the sequence reset and the format used.
        # This is needed to reassemble in the same batch yearly and continuous sequences that have
        # been split in multiple batches above because `seq` is the same counter for multiple
        # groups that might be spread in multiple months.
        final_batches = []
        for journal_group in grouped.values():
            for date_group in journal_group.values():
                if (
                    not final_batches
                    or final_batches[-1]['format'] != date_group['format']
                    or dict(final_batches[-1]['format_values'], seq=0) != dict(date_group['format_values'], seq=0)
                ):
                    final_batches += [date_group]
                elif date_group['reset'] == 'never':
                    final_batches[-1]['records'] += date_group['records']
                elif (
                    date_group['reset'] == 'year'
                    and (
                        final_batches[-1]['records'][0][self._sequence_date_field].year
                        == date_group['records'][0][self._sequence_date_field].year)
                ):
                    final_batches[-1]['records'] += date_group['records']
                else:
                    final_batches += [date_group]

        # Give the name based on previously computed values
        for batch in final_batches:
            for record in batch['records']:
                record[record._sequence_field] = batch['format'].format(**batch['format_values'])
                batch['format_values']['seq'] += 1
            batch['records']._compute_split_sequence()
