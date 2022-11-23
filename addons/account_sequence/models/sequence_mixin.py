from psycopg2 import DatabaseError

from odoo import models
from odoo.tools import mute_logger


class SequenceMixin(models.AbstractModel):
    _inherit = 'sequence.mixin'

    def _get_last_sequence(self, relaxed=False, with_prefix=None, lock=True):
        return super()._get_last_sequence(relaxed, with_prefix, False)

    def _set_next_sequence(self):
        # OVERRIDE
        self.ensure_one()
        last_sequence = self._get_last_sequence()
        new = not last_sequence
        if new:
            last_sequence = self._get_last_sequence(relaxed=True) or self._get_starting_sequence()

        format_string, format_values = self._get_sequence_format_param(last_sequence)
        if new:
            format_values['seq'] = 0
            format_values['year'] = self[self._sequence_date_field].year % (10 ** format_values['year_length'])
            format_values['month'] = self[self._sequence_date_field].month

        # before flushing inside the savepoint (which may be rolled back!), make sure everything
        # is already flushed, otherwise we could lose non-sequence fields values, as the ORM believes
        # them to be flushed.
        self.flush_recordset()
        while True:
            format_values['seq'] = format_values['seq'] + 1
            sequence = format_string.format(**format_values)
            try:
                with self.env.cr.savepoint(flush=False), mute_logger('odoo.sql_db'):
                    self[self._sequence_field] = sequence
                    self.flush_recordset([self._sequence_field])
                    break
            except DatabaseError as e:
                # 23P01 ExclusionViolation
                # 23505 UniqueViolation
                if e.pgcode not in ('23P01', '23505'):
                    raise e
        self._compute_split_sequence()
        self.flush_recordset(['sequence_prefix', 'sequence_number'])
