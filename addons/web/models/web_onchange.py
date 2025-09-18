"""Web onchange and form-processing operations on the base model.

Provides ``onchange`` (the webclient's onchange RPC entry point) and
``web_override_translations``.
"""

import itertools
from typing import Any

from odoo import models
from odoo.api import NewId
from odoo.fields import Command
from odoo.tools import OrderedSet, unique

from .record_snapshot import RecordSnapshot


class Base(models.AbstractModel):
    _inherit = "base"

    def onchange(
        self, values: dict, field_names: list[str], fields_spec: dict
    ) -> dict[str, Any]:
        """
        Perform an onchange on the given fields, and return the result.

        :param values: dictionary mapping field names to values on the form view,
            giving the current state of modification
        :param field_names: names of the modified fields
        :param fields_spec: dictionary specifying the fields in the view,
            just like the one used by :meth:`web_read`; it is used to format
            the resulting values

        When creating a record from scratch, the client should call this with an
        empty list as ``field_names``. In that case, the method first adds
        default values to ``values``, computes the remaining fields, applies
        onchange methods to them, and return all the fields in ``fields_spec``.

        The result is a dictionary with two optional keys. The key ``"value"``
        is used to return field values that should be modified on the caller.
        The corresponding value is a dict mapping field names to their value,
        in the format of :meth:`web_read`, except for x2many fields, where the
        value is a list of commands to be applied on the caller's field value.

        The key ``"warning"`` provides a warning message to the caller. The
        corresponding value is a dictionary like::

            {
                "title": "Be careful!",  # subject of message
                "message": "Blah blah blah.",  # full warning message
                "type": "dialog",  # how to display the warning
            }

        """
        # this is for tests using `Form`
        self.env.flush_all()

        env = self.env
        first_call = not field_names

        if not (self and self._name == "res.users"):
            # res.users defines SELF_WRITEABLE_FIELDS to give access to the user
            # to modify themselves, we skip the check in that case because the
            # user does not have write permission on themselves
            # TODO update res.users
            self.check_access("write" if self else "create")

        if any(fname not in self._fields for fname in field_names):
            return {}

        if first_call:
            field_names = [fname for fname in values if fname != "id"]
            missing_names = [fname for fname in fields_spec if fname not in values]
            defaults = self.default_get(missing_names)
            for field_name in missing_names:
                if field_name in defaults:
                    values[field_name] = defaults[field_name]
                    field_names.append(field_name)
                else:
                    field = self._fields[field_name]
                    if not field.compute or self.pool.field_depends[field]:
                        # don't assign computed fields without dependencies,
                        # otherwise they don't get computed
                        values[field_name] = False

        # prefetch x2many lines: this speeds up the initial snapshot by avoiding
        # computing fields on new records as much as possible, as that can be
        # costly and is not necessary at all
        self.fetch(fields_spec.keys())
        for field_name, field_spec in fields_spec.items():
            field = self._fields[field_name]
            if field.type not in ("one2many", "many2many"):
                continue
            sub_fields_spec = field_spec.get("fields") or {}
            if sub_fields_spec and values.get(field_name):
                # retrieve all line ids in commands
                line_ids = OrderedSet(self[field_name].ids)
                for cmd in values[field_name]:
                    if cmd[0] in (Command.UPDATE, Command.LINK):
                        line_ids.add(cmd[1])
                    elif cmd[0] == Command.SET:
                        line_ids.update(cmd[2])
                # prefetch stored fields on lines
                lines = self[field_name].browse(line_ids)
                lines.fetch(sub_fields_spec.keys())
                # copy the cache of lines to their corresponding new records;
                # this avoids computing computed stored fields on new_lines
                new_lines = lines.browse(map(NewId, line_ids))
                for sub_field_name in sub_fields_spec:
                    sub_field = lines._fields[sub_field_name]
                    for new_line, line in zip(new_lines, lines, strict=True):
                        line_value = sub_field.convert_to_cache(
                            line[sub_field_name], new_line, validate=False
                        )
                        sub_field._update_cache(new_line, line_value)

        # Isolate changed values, to handle inconsistent data sent from the
        # client side: when a form view contains two one2many fields that
        # overlap, the lines that appear in both fields may be sent with
        # different data. Consider, for instance:
        #
        #   foo_ids: [line with value=1, ...]
        #   bar_ids: [line with value=1, ...]
        #
        # If value=2 is set on 'line' in 'bar_ids', the client sends
        #
        #   foo_ids: [line with value=1, ...]
        #   bar_ids: [line with value=2, ...]
        #
        # The idea is to put 'foo_ids' in cache first, so that the snapshot
        # contains value=1 for line in 'foo_ids'. The snapshot is then updated
        # with the value of `bar_ids`, which will contain value=2 on line.
        #
        # The issue also occurs with other fields. For instance, an onchange on
        # a move line has a value for the field 'move_id' that contains the
        # values of the move, among which the one2many that contains the line
        # itself, with old values!
        #
        initial_values = dict(values)
        changed_values = {fname: initial_values.pop(fname) for fname in field_names}

        # do not force delegate fields to False
        for parent_name in self._inherits.values():
            if not initial_values.get(parent_name, True):
                initial_values.pop(parent_name)

        # create a new record with initial values
        if self:
            # fill in the cache of record with the values of self
            cache_values = {fname: self[fname] for fname in fields_spec}
            record = self.new(cache_values, origin=self)
            # apply initial values on top of the values of self
            record._update_cache(initial_values)
        else:
            # set changed values to null in initial_values; not setting them
            # triggers default_get() on the new record when creating snapshot0
            initial_values.update(dict.fromkeys(field_names, False))
            record = self.new(initial_values)

        # make parent records match with the form values; this ensures that
        # computed fields on parent records have all their dependencies at
        # their expected value
        for field_name in initial_values:
            field = self._fields.get(field_name)
            if field and field.inherited:
                parent_name, related_field_name = field.related.split(".", 1)
                if parent := record[parent_name]:
                    parent._update_cache({related_field_name: record[field_name]})

        # make a snapshot based on the initial values of record
        snapshot0 = RecordSnapshot(record, fields_spec, fetch=(not first_call))

        # store changed values in cache; also trigger recomputations based on
        # subfields (e.g., line.a has been modified, line.b is computed stored
        # and depends on line.a, but line.b is not in the form view)
        record._update_cache(changed_values)

        # update snapshot0 with changed values
        for field_name in field_names:
            snapshot0.fetch(field_name)

        # Determine which field(s) should be triggered an onchange. On the first
        # call, 'names' only contains fields with a default. If 'self' is a new
        # line in a one2many field, 'names' also contains the one2many's inverse
        # field, and that field may not be in nametree.
        todo = (
            list(unique(itertools.chain(field_names, fields_spec)))
            if first_call
            else list(field_names)
        )
        done = set()

        # mark fields to do as modified to trigger recomputations
        protected = [
            field
            for mod_field in [self._fields[fname] for fname in field_names]
            for field in self.pool.field_computed.get(mod_field) or [mod_field]
        ]
        with self.env.protecting(protected, record):
            record.modified(list(self._fields) if first_call else todo)
            for field_name in todo:
                field = self._fields[field_name]
                if field.inherited:
                    # modifying an inherited field should modify the parent
                    # record accordingly; because we don't actually assign the
                    # modified field on the record, the modification on the
                    # parent record has to be done explicitly
                    parent = record[field.related.split(".")[0]]
                    parent[field_name] = record[field_name]

        result = {"warnings": OrderedSet()}

        # process names in order
        while todo:
            # apply field-specific onchange methods
            for field_name in todo:
                record._apply_onchange_methods(field_name, result)
                done.add(field_name)

            if not env.context.get("recursive_onchanges", True):
                break

            # determine which fields to process for the next pass
            todo = [
                field_name
                for field_name in fields_spec
                if field_name not in done and snapshot0.has_changed(field_name)
            ]

        # make the snapshot with the final values of record
        snapshot1 = RecordSnapshot(record, fields_spec)

        # determine values that have changed by comparing snapshots
        result["value"] = snapshot1.diff(snapshot0, force=first_call)

        # format warnings
        warnings = result.pop("warnings")
        if len(warnings) == 1:
            title, message, type_ = warnings.pop()
            if not type_:
                type_ = "dialog"
            result["warning"] = {
                "title": title,
                "message": message,
                "type": type_,
            }
        elif len(warnings) > 1:
            # concatenate warning titles and messages
            title = self.env._("Warnings")
            message = "\n\n".join(
                [
                    warn_title + "\n\n" + warn_message
                    for warn_title, warn_message, warn_type in warnings
                ]
            )
            result["warning"] = {
                "title": title,
                "message": message,
                "type": "dialog",
            }

        return result

    def web_override_translations(self, values: dict[str, str]) -> None:
        """
        This method is used to override all the modal translations of the given fields
        with the provided value for each field.

        :param values: dictionary of the translations to apply for each field name
            ex: ``{ "field_name": "new_value" }``
        """
        self.ensure_one()
        for field_name in values:
            field = self._fields.get(field_name)
            if field and field.translate is True:
                translations = {
                    lang: False for lang, _ in self.env["res.lang"].get_installed()
                }
                translations["en_US"] = values[field_name]
                translations[self.env.lang or "en_US"] = values[field_name]
                self.update_field_translations(field_name, translations)
