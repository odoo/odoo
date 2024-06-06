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
        sequence_number_reset = self._deduce_sequence_number_reset(last_sequence)
        if new:
            date_start, date_end = self._get_sequence_date_range(sequence_number_reset)
            format_values['seq'] = 0
            format_values['year'] = self._truncate_year_to_length(date_start.year, format_values['year_length'])
            format_values['month'] = date_start.month
            format_values['year_end'] = self._truncate_year_to_length(date_end.year, format_values['year_end_length'])
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
