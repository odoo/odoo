import typing
from collections import defaultdict
from operator import attrgetter
from typing import override

from odoo.tools import OrderedSet, unique
from odoo.tools.sql import pg_varchar

from .base import Field
from .numeric import Integer
from .selection import Selection

if typing.TYPE_CHECKING:
    from ..models import BaseModel


class Reference(Selection):
    """Pseudo-relational field (no FK in database).

    The field value is stored as a :class:`string <str>` following the pattern
    ``"res_model,res_id"`` in database.
    """

    type = "reference"

    _column_type = ("varchar", pg_varchar())

    # Reference must bypass Selection.__get__ because convert_to_record is
    # non-trivial: it splits "model,id" and browses. The Selection shortcut
    # would return the raw string instead of a record.
    __get__ = Field.__get__

    @override
    def convert_to_column(self, value, record, values=None, validate=True):
        return Field.convert_to_column(self, value, record, values, validate)

    @override
    def convert_to_cache(self, value, record, validate=True):
        # cache format: str ("model,id") or None
        if hasattr(value, "_name") and hasattr(value, "_ids"):  # BaseModel instance
            if not validate or (
                value._name in self.get_values(record.env) and len(value) <= 1
            ):
                return f"{value._name},{value.id}" if value else None
        elif isinstance(value, str):
            res_model, res_id = value.split(",")
            if not validate or res_model in self.get_values(record.env):
                if record.env[res_model].browse(int(res_id)).exists():
                    return value
                else:
                    return None
        elif not value:
            return None
        raise ValueError(f"Wrong value for {self}: {value!r}")

    @override
    def convert_to_record(self, value, record):
        if value:
            res_model, res_id = value.split(",")
            return record.env[res_model].browse(int(res_id))
        return None

    @override
    def convert_to_read(self, value, record, use_display_name=True):
        return f"{value._name},{value.id}" if value else False

    @override
    def convert_to_export(self, value, record):
        return value.display_name if value else ""

    @override
    def convert_to_display_name(self, value, record):
        return value.display_name if value else False


class Many2oneReference(Integer):
    """Pseudo-relational field (no FK in database).

    The field value is stored as an :class:`integer <int>` id in database.

    Contrary to :class:`Reference` fields, the model has to be specified
    in a :class:`Char` field, whose name has to be specified in the
    `model_field` attribute for the current :class:`Many2oneReference` field.

    :param str model_field: name of the :class:`Char` where the model name is stored.
    """

    type = "many2one_reference"

    model_field = None
    aggregator = None

    _related_model_field = property(attrgetter("model_field"))

    _description_model_field = property(attrgetter("model_field"))

    @override
    def convert_to_cache(self, value, record, validate=True):
        # cache format: id or None
        if hasattr(value, "_ids"):  # BaseModel instance
            value = value._ids[0] if value._ids else None
        return super().convert_to_cache(value, record, validate)

    @override
    def _update_inverses(self, records: BaseModel, value):
        """Add `records` to the cached values of the inverse fields of `self`."""
        if not value:
            return
        model_ids = self._record_ids_per_res_model(records)

        for invf in records.pool.field_inverses[self]:
            records = records.browse(model_ids[invf.model_name])
            if not records:
                continue
            corecord = records.env[invf.model_name].browse(value)
            records = records.filtered_domain(invf.get_comodel_domain(corecord))
            if not records:
                continue
            ids0 = invf._get_cache(corecord.env).get(corecord.id)
            # if the value for the corecord is not in cache, but this is a new
            # record, assign it anyway, as you won't be able to fetch it from
            # database (see `test_sale_order`)
            if ids0 is not None or not corecord.id:
                ids1 = tuple(unique((ids0 or ()) + records._ids))
                invf._update_cache(corecord, ids1)

    def _record_ids_per_res_model(self, records: BaseModel) -> dict[str, OrderedSet]:
        model_ids = defaultdict(OrderedSet)
        for record in records:
            model = record[self.model_field]
            if not model and record._fields[self.model_field].compute:
                # fallback when the model field is computed :-/
                record._fields[self.model_field].compute_value(record)
                model = record[self.model_field]
                if not model:
                    continue
            model_ids[model].add(record.id)
        return model_ids
