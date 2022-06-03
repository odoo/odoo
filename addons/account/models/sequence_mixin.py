# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_date
from odoo.tools import frozendict

import re
from collections import defaultdict
from psycopg2 import sql


class SequenceMixin(models.AbstractModel):
    """Mechanism used to have an editable sequence number.

    Be careful of how you use this regarding the prefixes. More info in the
    docstring of _get_last_sequence.
    """

    _name = 'sequence.mixin'
    _description = "Automatic sequence"

    _sequence_field = "name"
    _sequence_date_field = "date"
    _sequence_index = False
    _sequence_monthly_regex = r'^(?P<prefix1>.*?)(?P<year>((?<=\D)|(?<=^))((19|20|21)\d{2}|(\d{2}(?=\D))))(?P<prefix2>\D*?)(?P<month>(0[1-9]|1[0-2]))(?P<prefix3>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$'
    _sequence_yearly_regex = r'^(?P<prefix1>.*?)(?P<year>((?<=\D)|(?<=^))((19|20|21)?\d{2}))(?P<prefix2>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$'
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

    @api.constrains(lambda self: (self._sequence_field, self._sequence_date_field))
    def _constrains_date_sequence(self):
        # Make it possible to bypass the constraint to allow edition of already messed up documents.
        # /!\ Do not use this to completely disable the constraint as it will make this mixin unreliable.
        constraint_date = fields.Date.to_date(self.env['ir.config_parameter'].sudo().get_param(
            'sequence.mixin.constraint_start_date',
            '1970-01-01'
        ))
        for record in self:
            date = fields.Date.to_date(record[record._sequence_date_field])
            sequence = record[record._sequence_field]
            if sequence and date and date > constraint_date:
                format_values = record._get_sequence_format_param(sequence)[1]
                if (
                    format_values['year'] and format_values['year'] != date.year % 10**len(str(format_values['year']))
                    or format_values['month'] and format_values['month'] != date.month
                ):
                    raise ValidationError(_(
                        "The %(date_field)s (%(date)s) doesn't match the sequence number of the related %(model)s (%(sequence)s)\n"
                        "You will need to clear the %(model)s's %(sequence_field)s to proceed.\n"
                        "In doing so, you might want to resequence your entries in order to maintain a continuous date-based sequence.",
                        date=format_date(self.env, date),
                        sequence=sequence,
                        date_field=record._fields[record._sequence_date_field]._description_string(self.env),
                        sequence_field=record._fields[record._sequence_field]._description_string(self.env),
                        model=self.env['ir.model']._get(record._name).display_name,
                    ))

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
        for regex, ret_val, requirements in [
            (self._sequence_monthly_regex, 'month', ['seq', 'month', 'year']),
            (self._sequence_yearly_regex, 'year', ['seq', 'year']),
            (self._sequence_fixed_regex, 'never', ['seq']),
        ]:
            match = re.match(regex, name or '')
            if match:
                groupdict = match.groupdict()
                if all(req in groupdict for req in requirements):
                    return ret_val
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

    def _get_last_sequence(self, relaxed=False, with_prefix=None, lock=True):
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
        :param with_prefix: The sequence prefix to restrict the search on, if any.

        :return: the string of the previous sequence or None if there wasn't any.
        """
        self.ensure_one()
        if self._sequence_field not in self._fields or not self._fields[self._sequence_field].store:
            raise ValidationError(_('%s is not a stored field', self._sequence_field))
        where_string, param = self._get_last_sequence_domain(relaxed)
        if self.id or self.id.origin:
            where_string += " AND id != %(id)s "
            param['id'] = self.id or self.id.origin
        if with_prefix is not None:
            where_string += " AND sequence_prefix = %(with_prefix)s "
            param['with_prefix'] = with_prefix

        query = f"""
                SELECT {{field}} FROM {self._table}
                {where_string}
                AND sequence_prefix = (SELECT sequence_prefix FROM {self._table} {where_string} ORDER BY id DESC LIMIT 1)
                ORDER BY sequence_number DESC
                LIMIT 1
        """
        if lock:
            query = f"""
            UPDATE {self._table} SET write_date = write_date WHERE id = (
                {query.format(field='id')}
            )
            RETURNING {self._sequence_field};
            """
        else:
            query = query.format(field=self._sequence_field)

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

    def _is_last_from_seq_chain(self):
        """Tells whether or not this element is the last one of the sequence chain.

        :return: True if it is the last element of the chain.
        """
        last_sequence = self._get_last_sequence(with_prefix=self.sequence_prefix)
        if not last_sequence:
            return True
        seq_format, seq_format_values = self._get_sequence_format_param(last_sequence)
        seq_format_values['seq'] += 1
        return seq_format.format(**seq_format_values) == self.name

    def _is_end_of_seq_chain(self):
        """Tells whether or not these elements are the last ones of the sequence chain.

        :return: True if self are the last elements of the chain.
        """
        batched = defaultdict(lambda: {'last_rec': self.browse(), 'seq_list': []})
        for record in self.filtered(lambda x: x[x._sequence_field]):
            seq_format, format_values = record._get_sequence_format_param(record[record._sequence_field])
            seq = format_values.pop('seq')
            batch = batched[(seq_format, frozendict(format_values))]
            batch['seq_list'].append(seq)
            if batch['last_rec'].sequence_number <= record.sequence_number:
                batch['last_rec'] = record

        for values in batched.values():
            # The sequences we are deleting are not sequential
            seq_list = values['seq_list']
            if max(seq_list) - min(seq_list) != len(seq_list) - 1:
                return False

            # last_rec must have the highest number in the database
            record = values['last_rec']
            if not record._is_last_from_seq_chain():
                return False
        return True
