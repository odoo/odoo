# -*- coding: utf-8 -*-
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_date

from odoo.tools import frozendict, mute_logger, date_utils, get_fiscal_year
import re
from collections import defaultdict
from psycopg2 import sql, DatabaseError


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
    _sequences = [
        (r'^(?P<prefix1>.*?)(?P<year>({year}))(?P<prefix2>\D*?)(?P<month>{month})(?P<prefix3>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$', 'month'),
        (r'^(?P<prefix1>.*?)(?P<year2>({year2}))(?P<prefix2>\D*?)(?P<month>{month})(?P<prefix3>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$', 'month'),
        # Detecting fiscal year based on current date so use 4 format for fiscal year
        (r'^(?P<prefix1>.*?)(?P<fyear_start>\d{{4}})(?P<prefix2>\D+?)(?P<fyear_end>({fyear_end}))(?P<prefix3>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$', 'fyear'),
        (r'^(?P<prefix1>.*?)(?P<fyear_start>({fyear_start}))(?P<prefix2>\D+?)(?P<fyear_end>(\d{{4}}))(?P<prefix3>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$', 'fyear'),
        (r'^(?P<prefix1>.*?)(?P<fyear_start2>\d{{2}})(?P<prefix2>\D+?)(?P<fyear_end2>({fyear_end2}))(?P<prefix3>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$', 'fyear'),
        (r'^(?P<prefix1>.*?)(?P<fyear_start2>({fyear_start2}))(?P<prefix2>\D+?)(?P<fyear_end2>(\d{{2}}))(?P<prefix3>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$', 'fyear'),
        # Year at last so not conflict with fiscal year
        (r'^(?P<prefix1>.*?)(?P<year>({year}))(?P<prefix2>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$', 'year'),
        (r'^(?P<prefix1>.*?)(?P<year2>({year2}))(?P<prefix2>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$', 'year'),
        (r'^(?P<prefix1>.*?)(?P<seq>\d+)(?P<suffix>\D*?)$', 'never')
    ]

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

    def _get_sequence_date_range(self, reset):
        ref_date = fields.Date.to_date(self[self._sequence_date_field])
        if reset in ('year', 'year_range'):
            return (date(ref_date.year, 1, 1), date(ref_date.year, 12, 31))
        if reset == 'month':
            return date_utils.get_month(ref_date)
        if reset == 'never':
            return (date(1, 1, 1), date(9999, 1, 1))
        raise NotImplementedError(reset)

    def _must_check_constrains_date_sequence(self):
        return True

    def _year_match(self, format_value, date):
        return format_value == self._truncate_year_to_length(date.year, len(str(format_value)))

    def _truncate_year_to_length(self, year, length):
        return year % (10 ** length)

    def _sequence_matches_date(self):
        self.ensure_one()
        date = fields.Date.to_date(self[self._sequence_date_field])
        sequence = self[self._sequence_field]
        previous = self._get_last_sequence(with_prefix=self.sequence_prefix)
        if not sequence or not date or not previous or sequence=='/':
            return True

        return previous._find_sequence()[1] == self._find_sequence()[1]

    @api.constrains(lambda self: (self._sequence_field, self._sequence_date_field))
    def _constrains_date_sequence(self):
        # Make it possible to bypass the constraint to allow edition of already messed up documents.
        # /!\ Do not use this to completely disable the constraint as it will make this mixin unreliable.
        constraint_date = fields.Date.to_date(self.env['ir.config_parameter'].sudo().get_param(
            'sequence.mixin.constraint_start_date',
            '1970-01-01'
        ))
        for record in self:
            if not record._must_check_constrains_date_sequence():
                continue
            if not record._sequence_matches_date():
                raise ValidationError(_(
                    "The %(date_field)s (%(date)s) doesn't match the sequence number of the related %(model)s (%(sequence)s)\n"
                    "You will need to clear the %(model)s's %(sequence_field)s to proceed.\n"
                    "In doing so, you might want to resequence your entries in order to maintain a continuous date-based sequence.",
                    date=format_date(self.env, record[record._sequence_date_field]),
                    sequence=record[record._sequence_field],
                    date_field=record._fields[record._sequence_date_field]._description_string(self.env),
                    sequence_field=record._fields[record._sequence_field]._description_string(self.env),
                    model=self.env['ir.model']._get(record._name).display_name,
                ))

    @api.depends(lambda self: [self._sequence_field])
    def _compute_split_sequence(self):
        for record in self:
            matching = re.match(r'^((?:.*?))(\d{0,9})(?:\D*?)$', record[record._sequence_field] or '')
            record.sequence_prefix = matching.group(1)
            record.sequence_number = int(matching.group(2) or 0)

    def _deduce_sequence_number_reset(self):
        return self and self._find_sequence()[1] or 'never'

    def _get_sequence_keys(self):
        self.ensure_one()
        date = self[self._sequence_date_field]
        fyear_start = fyear_end = ''
        if 'company_id' in self._fields:
            company = self.company_id
            fyear_start, fyear_end = get_fiscal_year(date, day=company.fiscalyear_last_day, month=int(company.fiscalyear_last_month))
        return {
            'year': date.strftime('%Y'),
            'year2': date.strftime('%Y')[-2:],
            'month': date.strftime('%m'),
            'fyear_start': fyear_start.strftime('%Y'),
            'fyear_start2': fyear_start.strftime('%Y')[-2:],
            'fyear_end': fyear_end.strftime('%Y'),
            'fyear_end2': fyear_end.strftime('%Y')[-2:],
        }

    def _find_sequence(self, sequence=None):
        self.ensure_one()
        data = self._get_sequence_keys()
        for regex, *others in self._sequences:
            rex = regex.format(**data)
            matching = re.match(rex, sequence or self[self._sequence_field])
            if matching:
                return matching, *others
        raise ValidationError(_('No number found in the sequence.'))

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

    def _get_last_sequence(self, relaxed=False, with_prefix=None):
        """Retrieve the record having the previous sequence.

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

        :return: record having the previous sequence or BrowseNULL if there wasn't any.
        """
        self.ensure_one()
        if self._sequence_field not in self._fields or not self._fields[self._sequence_field].store:
            raise ValidationError(_('%s is not a stored field', self._sequence_field))
        where_string, param = self._get_last_sequence_domain(relaxed)
        if self._origin.id:
            where_string += " AND id != %(id)s "
            param['id'] = self._origin.id
        if with_prefix is not None:
            where_string += " AND sequence_prefix = %(with_prefix)s "
            param['with_prefix'] = with_prefix

        query = f"""
                SELECT id FROM {self._table}
                {where_string}
                ORDER BY date DESC, sequence_number DESC
                LIMIT 1
        """
        self.flush_model([self._sequence_field, 'sequence_number', 'sequence_prefix'])
        self.env.cr.execute(query, param)
        rid = self.env.cr.fetchone()
        if not rid:
            return None
        return self.browse(rid[0])

    def _set_next_sequence(self):
        """Set the next sequence.

        This method ensures that the field is set both in the ORM and in the database.
        This is necessary because we use a database query to get the previous sequence,
        and we need that query to always be executed on the latest data.

        :param field_name: the field that contains the sequence.
        """
        self.ensure_one()
        data = self._get_sequence_keys()
        previous = self._get_last_sequence()
        if previous:
            sequence = int(previous.sequence_number)
        else:
            previous = self._get_last_sequence(relaxed=True)
            sequence = 0

        seq_fmt = ['', 5, '']   # prefix, seq #digits, suffix
        if not previous:
            seq_fmt = list(re.match(r'^((?:.*?))(0+)((?:\D*?))$', self._get_starting_sequence()).groups())
            seq_fmt[1] = len(seq_fmt[1])
        else:
            seq_pos = 0
            matching, period = previous._find_sequence()
            for key, val in matching.groupdict().items():
                if key=='seq':
                    seq_fmt[1] = len(val)
                    seq_pos = 2
                    continue
                if sequence == 0 and key in ('year', 'year2', 'fyear_start', 'fyear_end'):
                    val = str(int(val) + 1).zfill(len(val))
                seq_fmt[seq_pos] += data.get(key, val)

        # before flushing inside the savepoint (which may be rolled back!), make sure everything
        # is already flushed, otherwise we could lose non-sequence fields values, as the ORM believes
        # them to be flushed.
        self.flush_recordset()
        # because we are flushing, and because the business code might be flushing elsewhere (i.e. to
        # validate constraints), the fields depending on the sequence field might be protected by the
        # ORM. This is not desired, so we already reset them here.
        registry = self.env.registry
        triggers = registry._field_triggers[self._fields[self._sequence_field]]
        for inverse_field, triggered_fields in triggers.items():
            for triggered_field in triggered_fields:
                if not triggered_field.store or not triggered_field.compute:
                    continue
                for field in registry.field_inverses[inverse_field[0]] if inverse_field else [None]:
                    self.env.add_to_compute(triggered_field, self[field.name] if field else self)
        while True:
            sequence += 1
            try:
                with self.env.cr.savepoint(flush=False), mute_logger('odoo.sql_db'):
                    self[self._sequence_field] = seq_fmt[0] + str(sequence).zfill(seq_fmt[1]) + seq_fmt[2]
                    self.flush_recordset([self._sequence_field])
                    break
            except DatabaseError as e:
                # 23P01 ExclusionViolation
                # 23505 UniqueViolation
                print('Retry')
                if e.pgcode not in ('23P01', '23505'):
                    raise e
        self._compute_split_sequence()
        self.flush_recordset(['sequence_prefix', 'sequence_number'])

    def _get_new_sequence(self, matching, sequence):
        """Get the new sequence.

        This method is used to compute the new sequence when the user changes the sequence
        manually. It is used in the onchange of the sequence field.

        :param sequence: the new sequence.
        :return: the new sequence.
        """
        self.ensure_one()
        data = self._get_sequence_keys()
        seq_fmt = ['', 5, '']   # prefix, seq #digits, suffix
        seq_pos = 0
        for key, val in matching.groupdict().items():
            if key=='seq':
                seq_fmt[1] = len(val)
                seq_pos = 2
                continue
            seq_fmt[seq_pos] += data.get(key, val)
        return seq_fmt[0] + str(sequence).zfill(seq_fmt[1]) + seq_fmt[2]

