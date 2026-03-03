from __future__ import annotations

import typing

from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import MissingError
from odoo.tools import clean_context, ormcache

if typing.TYPE_CHECKING:
    from odoo.api import ValuesType
    from odoo.models import BaseModel
    from collections.abc import Iterable


class MailTrackMixin(models.AbstractModel):
    """ Base class enabling value tracking on models. What to do with values
    is left to child model. Consider inheriting from 'mail.thread' which
    link them to messages. """
    _name = 'mail.track.mixin'
    _description = 'Mail Track Mixin'

    # model / crud helpers
    # ------------------------------------------------------

    def _fallback_lang(self) -> BaseModel:
        if not self.env.context.get("lang"):
            return self.with_context(lang=self.env.user.lang)
        return self

    def _valid_field_parameter(self, field, name):
        # allow tracking on models inheriting from 'mail.thread'
        return name == 'tracking' or super()._valid_field_parameter(field, name)

    # track data storage / manipulation
    # ------------------------------------------------------

    def _track_disabled(self):
        return self.env.context.get('tracking_disable') or self.env.context.get('mail_notrack')

    def _track_prepare(self, field_names: Iterable[str]) -> dict[int, ValuesType]:
        """ Prepare the tracking of `fields_iter` for `self` for tracked
        fields (see `_track_get_fields`). Store initial values for tracked fields
        in precommit data.

        :param Iterable[str] field_names: field names to potentially track, to be
            checked against model-based tracked fields
        """
        tracked_fnames = self._track_get_fields().intersection(field_names)
        if not self or not tracked_fnames:
            return
        self.env.cr.precommit.add(self._track_finalize)
        initial_values = self.env.cr.precommit.data.setdefault(f'mail.tracking.{self._name}', {})
        for record in self.sudo().filtered(lambda r: r.id):  # be sure to compute initial values whatever current user ACLs
            record_values = initial_values.setdefault(record.id, {})
            if record_values is not None:  # None means tracking was disabled for this record
                for fname in tracked_fnames:
                    record_values.setdefault(fname, record._track_convert_value(fname, record[fname]))

        # ease overrides by returning initial values
        return initial_values

    def _track_clear(self):
        """ Clear tracking data, without preventing further other tracking. """
        self.env.cr.precommit.data.pop(f'mail.tracking.{self._name}', None)

    def _track_discard(self):
        """ Prevent any tracking of fields on `self`. """
        if not self or not self._track_get_fields():
            return
        self.env.cr.precommit.add(self._track_finalize)
        initial_values = self.env.cr.precommit.data.setdefault(f'mail.tracking.{self._name}', {})
        # disable tracking by setting initial values to None
        for id_ in self.ids:
            initial_values[id_] = None

    def _track_execute(
        self, track_init_values: dict[int, ValuesType],
        trackings: dict[int, tuple[set[str], list[ValuesType]]]
    ):
        """ Perform model specific code based on trackings.

        :param dict[int, ValuesType] track_init_values: mapping {record_id: initial_values}
            where initial_values is a dict {field_name: value, ... } containing
            all initial values;
        :param dict[int, tuple[set[str], list[ValuesType]]] trackings: for
            each existing record, changes and generated tracking values;
        """
        return

    def _track_finalize(self) -> dict[int, ValuesType] | None:
        """ Generate the trackings for the records that have been prepared
        with `_tracking_prepare`.

        Also cleans precommit data, resetting state and avoiding multiple
        tracking generation. """
        # pop now, so that potentially nested calls do not loop (e.g. override a track
        # to generate sub-trackings)
        initial_values = self.env.cr.precommit.data.pop(f'mail.tracking.{self._name}', {})
        ids = [id_ for id_, vals in initial_values.items() if vals]
        if not ids:
            return

        fnames = self._track_get_fields()
        if not fnames:
            return

        # Clean the context to get rid of residual default_* keys that could
        # cause issues afterward during the mail.message generation. Example:
        # 'default_parent_id' would refer to the parent_id of the current
        # record that was used during its creation, but could refer to wrong
        # parent message id, leading to a traceback or a wrongly referenced
        # record
        # sudo: # be sure to compute end values whatever current user ACLs
        records_su = self.with_context(clean_context(self.env.context)).browse(ids).sudo()._fallback_lang()

        tracked_fields_get = records_su.fields_get(fnames, attributes=('string', 'type', 'selection', 'currency_field'))
        trackings = dict()
        for record_su in records_su:
            try:
                trackings[record_su.id] = record_su._mail_track(tracked_fields_get, initial_values[record_su.id])
            except MissingError:
                continue

        # launch business flow to manage tracking values
        records_su._track_execute(initial_values, trackings)

        self._track_clear()
        return records_su, initial_values, trackings

    @ormcache('self.env.uid', 'self.env.su')
    def _track_get_fields(self) -> set[str]:
        """ Return the set of tracked fields names for the current model. """
        model_fields = {
            name
            for name, field in self._fields.items()
            if getattr(field, 'tracking', None)
        }
        # track the properties changes ONLY if the parent changed
        model_fields |= {
            fname for fname, f in self._fields.items()
            if f.type == "properties"
            and f.definition_record in model_fields
            and getattr(f, "tracking", None) is not False
        }

        return model_fields and set(self.fields_get(model_fields, attributes=()))

    # track values generation
    # ------------------------------------------------------

    def _mail_track(
            self, tracked_fields_get: dict[str, ValuesType], initial_values: ValuesType
        ) -> tuple[set[str], list[ValuesType]]:
        """ For a given record, fields to check (tuple column name, column info)
        and initial values, return a valid command to create tracking values.
        The method accepts a single record or an empty one (where all field
        values will be falsy).

        :param dict[str, ValuesType] tracked_fields_get: fields_get of updated
            fields on which tracking is checked and performed;
        :param ValuesType initial_values: dict of initial values for each updated
            fields;

        :return: a tuple (changes, tracking_value_ids) where
          changes: set of updated column names; contains onchange tracked fields
          that changed;
          tracking_values: a values to create ``mail.tracking.value`` records;
        """
        if len(self) > 1:
            raise ValueError(f"Expected empty or single record: {self}")
        updated = set()
        tracking_values = []

        fields_track_info = self._mail_track_order_fields(tracked_fields_get)
        for col_name, _sequence in fields_track_info:
            if col_name not in initial_values:
                continue
            initial_value = initial_values[col_name]
            new_value = self._track_convert_value(col_name, self[col_name])
            if new_value == initial_value or (not new_value and not initial_value):  # because browse null != False
                continue

            if self._fields[col_name].type == "properties":
                definition_record_field = self._fields[col_name].definition_record
                if self[definition_record_field] == initial_values[definition_record_field]:
                    # track the change only if the parent changed
                    continue

                updated.add(col_name)
                tracking_values.extend(
                    self._create_mail_tracking_values_property(property_, col_name, tracked_fields_get[col_name])
                    # Show the properties in the same order as in the definition
                    for property_ in initial_value[::-1]
                    if property_['type'] not in ('separator', 'html', 'signature') and property_.get('value')
                )
                continue

            updated.add(col_name)
            tracking_values.append(self._create_mail_tracking_values(
                initial_value, new_value,
                col_name, tracked_fields_get[col_name],
            ))

        return updated, tracking_values

    def _mail_track_order_fields(
            self,
            tracked_fields_get: dict[str, ValuesType]
        ) -> list[tuple[str, int]]:
        """ Order tracking, based on sequence found on field definition. When
        having several identical sequences, properties are added after,
        and then field name is used. """
        fields_track_info = [
            (col_name, self._mail_track_get_field_sequence(col_name))
            for col_name in tracked_fields_get
        ]
        # sorting: sequence ASC, name ASC (higher sequence -> displayed last, then
        # order by name). Model order being id DESC (aka: first insert -> last
        # displayed) insert should be done by descending sequence then descending
        # name.
        fields_track_info.sort(key=lambda item: (
            item[1],
            tracked_fields_get[item[0]]['type'] != 'properties',
            item[0],
        ), reverse=True)
        return fields_track_info

    def _track_convert_value(self, fname: str, value: typing.Any) -> typing.Any:
        # get the properties definition with the value
        # (not just the dict with the value)
        if len(self) > 1:
            raise ValueError(f"Expected empty or single record: {self}")
        if (field := self._fields[fname]).type == 'properties':
            return field.convert_to_read(value, self)
        return value

    def _mail_track_get_field_sequence(self, fname: str) -> int:
        """ Find tracking sequence of a given field, given their name. Current
        parameter 'tracking' should be an integer, but attributes with True
        are still supported; old naming 'track_sequence' also. """
        if fname not in self._fields:
            return 100

        def get_field_sequence(fname):
            return getattr(
                self._fields[fname], 'tracking',
                getattr(self._fields[fname], 'track_sequence', True)
            )

        sequence = get_field_sequence(fname)
        if self._fields[fname].type == 'properties' and sequence is True:
            # default properties sequence is after the definition record
            parent_sequence = get_field_sequence(self._fields[fname].definition_record)
            return 100 if parent_sequence is True else parent_sequence
        return 100 if sequence is True else sequence

    # track value management
    # ------------------------------------------------------

    def _create_mail_tracking_values(
            self,
            initial_value: typing.Any, new_value: typing.Any,
            col_name: str, col_info: ValuesType,
        ) -> ValuesType:
        """ Prepare values to create a mail.tracking.value. It prepares old and
        new value according to the field type.

        :param Any initial_value: field value before the change. Relational
            fields should contain RecordSets;
        :param Any new_value: field value after the change. Relational fields
            should contain RecordSets;
        :param str col_name: technical field name, column name (e.g. 'user_id);
        :param ValuesType col_info: result of fields_get(col_name);

        :return: a dict of values valid for `mail.tracking.value` creation;
        """
        field = self.env['ir.model.fields']._get(self._name, col_name)
        if not field:
            raise ValueError(f'Unknown field {col_name} on model {self._name}')

        # field information (to be popped, kept for post processing)
        values = {
            'field_id': field.id,
            'field_name': col_name,
            'field_type': col_info['type'],
            'old_value': initial_value,
            'new_value': new_value,
        }

        if col_info['type'] in {'integer', 'float', 'char', 'text', 'datetime'}:
            values.update({
                f'old_value_{col_info["type"]}': initial_value,
                f'new_value_{col_info["type"]}': new_value
            })
        elif col_info['type'] == 'monetary':
            values.update({
                'currency_id': self[col_info['currency_field']].id,
                'old_value_float': initial_value,
                'new_value_float': new_value
            })
        elif col_info['type'] == 'date':
            values.update({
                'old_value_datetime': initial_value and fields.Datetime.to_string(datetime.combine(fields.Date.from_string(initial_value), datetime.min.time())) or False,
                'new_value_datetime': new_value and fields.Datetime.to_string(datetime.combine(fields.Date.from_string(new_value), datetime.min.time())) or False,
            })
        elif col_info['type'] == 'boolean':
            values.update({
                'old_value_integer': initial_value,
                'new_value_integer': new_value
            })
        elif col_info['type'] == 'selection':
            values.update({
                'old_value_char': initial_value and dict(col_info['selection']).get(initial_value, initial_value) or '',
                'new_value_char': new_value and dict(col_info['selection'])[new_value] or ''
            })
        elif col_info['type'] == 'many2one':
            # Can be:
            # - False value
            # - recordset, in case of standard field
            # - (id, display name), in case of properties (read format)
            if not initial_value:
                initial_value = (0, '')
            elif isinstance(initial_value, models.BaseModel):
                initial_value = (initial_value.id, initial_value.display_name)

            if not new_value:
                new_value = (0, '')
            elif isinstance(new_value, models.BaseModel):
                new_value = (new_value.id, new_value.display_name)

            values.update({
                'old_value_integer': initial_value[0],
                'new_value_integer': new_value[0],
                'old_value_char': initial_value[1],
                'new_value_char': new_value[1]
            })
        elif col_info['type'] in {'one2many', 'many2many', 'tags'}:
            # Can be:
            # - False value
            # - recordset, in case of standard field
            # - [(id, display name), ...], in case of properties (read format)
            model_name = self.env['ir.model']._get(field.relation).display_name
            if not initial_value:
                old_value_char = ''
            elif isinstance(initial_value, models.BaseModel):
                old_value_char = ', '.join(
                    value.display_name or self.env._(
                        'Unnamed %(record_model_name)s (%(record_id)s)',
                        record_model_name=model_name, record_id=value.id
                    )
                    for value in initial_value
                )
            else:
                old_value_char = ', '.join(value[1] for value in initial_value)
            if not new_value:
                new_value_char = ''
            elif isinstance(new_value, models.BaseModel):
                new_value_char = ', '.join(
                    value.display_name or self.env._(
                        'Unnamed %(record_model_name)s (%(record_id)s)',
                        record_model_name=model_name, record_id=value.id
                    )
                    for value in new_value
                )
            else:
                new_value_char = ', '.join(value[1] for value in new_value)

            values.update({
                'old_value_char': old_value_char,
                'new_value_char': new_value_char,
            })
        else:
            raise NotImplementedError(f'Unsupported tracking on field {field.name} (type {col_info["type"]}')

        return values

    def _create_mail_tracking_values_property(
        self, initial_value: typing.Any, col_name: str, col_info: ValuesType,
    ) -> ValuesType:
        """Generate the values for the <mail.tracking.values> corresponding to a property."""
        col_info = col_info | {'type': initial_value['type'], 'selection': initial_value.get('selection')}

        field_info = {
            'desc': f"{col_info['string']}: {initial_value['string']}",
            'name': col_name,
            'type': initial_value['type'],
        }
        value = initial_value.get('value', False)
        if value and initial_value['type'] == 'tags':
            value = [t for t in initial_value.get('tags', []) if t[0] in value]

        tracking_values = self._create_mail_tracking_values(
            value, False, col_name, col_info,
        )
        return {**tracking_values, 'field_info': field_info}

    # track value formatting
    # ------------------------------------------------------

    @api.model
    def _tracking_value_format_model(self, tracking_values: BaseModel) -> list[ValuesType]:
        """ Return structured formatted data to be used by chatter to display
        tracking values on a single model. Order it based on ascending sequence
        then field name. Property fields are always last.

        :returns: for each tracking value in self, their formatted display
          values given as a dict;
        :rtype: list[ValuesType]
        """
        if not tracking_values:
            return []

        # fetch model-based information
        if self._name not in ('mail.thread', 'mail.track.mixin'):
            tracked_fields = self.fields_get(tracking_values.field_id.mapped('name'), attributes={'digits', 'string', 'type'})
            model_sequence_info = dict(self._mail_track_order_fields(tracked_fields))
        else:
            tracked_fields, model_sequence_info = {}, {}

        # generate sequence of trackings
        fields_sequence_map = dict(
            {
                tracking.field_info['name']: tracking.field_info.get('sequence', 100)
                for tracking in tracking_values.filtered('field_info')
            },
            **model_sequence_info,
        )
        # generate dict of field information, if available
        fields_col_info = (
            tracking.field_id.ttype != 'properties'
            and tracked_fields.get(tracking.field_id.name)
            or {
                'string': tracking.field_info['desc'] if tracking.field_info else tracking_values.env._('Unknown'),
                'type': tracking.field_info['type'] if tracking.field_info else 'char',
            } for tracking in tracking_values
        )

        def sort_tracking_info(tracking_info_tuple):
            tracking = tracking_info_tuple[0]
            field_name = tracking.field_id.name or (tracking.field_info['name'] if tracking.field_info else 'unknown')
            return (
                fields_sequence_map.get(field_name, 100),
                tracking.field_id.ttype == 'properties',
                field_name,
            )

        formatted = [
            {
                'id': tracking.id,
                'fieldInfo': {
                    'changedField': col_info['string'],
                    'currencyId': tracking.currency_id.id,
                    'floatPrecision': col_info.get('digits'),
                    'fieldType': col_info['type'],
                    'isPropertyField': tracking.field_id.ttype == 'properties',
                },
                'newValue': self._format_display_value(tracking, col_info['type'], new=True)[0],
                'oldValue': self._format_display_value(tracking, col_info['type'], new=False)[0],
            }
            for tracking, col_info in sorted(zip(tracking_values, fields_col_info), key=sort_tracking_info)
        ]
        return formatted

    @api.model
    def _format_display_value(self, trackings, field_type: str, new: bool = True) -> str:
        """ Format value of 'mail.tracking.value', according to the field type.

        :param str field_type: Odoo field type;
        :param bool new: if True, display the 'new' value. Otherwise display
          the 'old' one.
        """
        field_mapping = {
            'boolean': ('old_value_integer', 'new_value_integer'),
            'date': ('old_value_datetime', 'new_value_datetime'),
            'datetime': ('old_value_datetime', 'new_value_datetime'),
            'char': ('old_value_char', 'new_value_char'),
            'float': ('old_value_float', 'new_value_float'),
            'integer': ('old_value_integer', 'new_value_integer'),
            'monetary': ('old_value_float', 'new_value_float'),
            'text': ('old_value_text', 'new_value_text'),
        }

        result = []
        for record in trackings:
            value_fname = field_mapping.get(
                field_type, ('old_value_char', 'new_value_char')
            )[bool(new)]
            value = record[value_fname]

            if field_type in {'integer', 'float', 'char', 'text', 'monetary'}:
                result.append(value)
            elif field_type in {'date', 'datetime'}:
                if not record[value_fname]:
                    result.append(value)
                elif field_type == 'date':
                    result.append(fields.Date.to_string(value))
                else:
                    result.append(f'{value}Z')
            elif field_type == 'boolean':
                result.append(bool(value))
            else:
                result.append(value)
        return result
