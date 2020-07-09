from odoo import fields
from odoo.tools import config
from odoo.tools.misc import monkey_patch

import logging
import datetime

_logger = logging.getLogger(__name__)

class FieldValue(object):
    def init_vals(self, field, env):
        self._field = field
        self._env = env
        self._test = bool(config['test_enable'] or config['test_file'])

    def no_test(self):
        self._test = False
        return self

class SelectionValue(str, FieldValue):
    def __eq__(self, other):
        val = super().__eq__(other)
        if not self._test:
            return val
        if val:
            return True
        try:
            selection = self._selection
        except AttributeError:
            self._selection = set(self._field.get_values(self._env))
            selection = self._selection
        if isinstance(other, str) and other not in selection:
            _logger.warning(
                "Comparing selection field %s with invalid value: %s\n"
                "Valid values are: %s" % (
                    self._field,
                    other,
                    ', '.join(selection),
                )
            )
        return False

    def __hash__(self):
        return str.__hash__(self)

class DateAndDatetimeValue(FieldValue):
    def __eq__(self, other):
        val = super().__eq__(other)
        if not self._test:
            return val
        if other and val == NotImplemented:
            _logger.warning("Comparing date field with '%s' %s on %s is not supported" % (
                other,
                type(other),
                self._field),
            )
        return val

class DateValue(DateAndDatetimeValue, datetime.date):
    def __hash__(self):
        return datetime.date.__hash__(self)

class DateTimeValue(DateAndDatetimeValue, datetime.datetime):
    def __hash__(self):
        return datetime.datetime.__hash__(self)


test_patches = {
    fields.Selection: SelectionValue,
    fields.Date: DateValue,
    fields.Datetime: DateTimeValue,
}

# Monkey path the convert_to_cache of fields to detect wrong
# comparisons. (i.e. deprecated values, typos, wrong field,...)
for patched_class, patching_class in test_patches.items():
    def patch_context(patched_class, patching_class):
        @monkey_patch(patched_class)
        def convert_to_cache(self, value, record, validate=True):
            value = convert_to_cache.super(self, value, record, validate)
            if value:
                if isinstance(value, str):
                    value = patching_class(value)
                elif isinstance(value, datetime.datetime):
                    value = patching_class(value.year, value.month, value.day, value.hour, value.minute, value.second, value.microsecond, value.tzinfo)
                elif isinstance(value, datetime.date):
                    value = patching_class(value.year, value.month, value.day)
                value.init_vals(self, record.env)
            return value
    patch_context(patched_class, patching_class)
