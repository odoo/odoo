from __future__ import annotations

import typing

from odoo import models
from odoo.exceptions import MissingError
from odoo.tools import clean_context, ormcache

if typing.TYPE_CHECKING:
    from odoo.api import CommandValue, ValuesType
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
        trackings: dict[int, tuple[set[str], list[CommandValue]]]
    ):
        """ Perform model specific code based on trackings.
        
        :param dict[int, ValuesType] track_init_values: mapping {record_id: initial_values}
            where initial_values is a dict {field_name: value, ... } containing
            all initial values;
        :param dict[int, tuple[set[str], list[CommandValue]]] trackings: for
            each existing record, changes and generated tracking values;
        """
        return

    def _track_finalize(self) -> dict[int, ValuesType] | None:
        """ Generate the trackings for the records that have been prepared
        with `_tracking_prepare`.

        Also cleans precommit data, resetting state and avoiding multiple
        tracking generation. """
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
