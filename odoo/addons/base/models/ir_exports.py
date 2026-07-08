# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools

from odoo import api, fields, models


class IrExports(models.Model):
    _name = 'ir.exports'
    _description = 'Exports'
    _order = 'name, id'

    name = fields.Char(string='Export Name')
    resource = fields.Char(index=True)
    export_fields = fields.One2many('ir.exports.line', 'export_id', string='Export ID', copy=True)
    export_language_ids = fields.Many2many(
        'res.lang', string='Languages',
        help="Each translatable field of the template is exported with one extra "
             "column per selected language, using the import convention (field@lang).")

    @api.model
    def _get_property_fields(self, fields, model, domain=()):
        """ Return property fields existing for the `domain` """
        property_fields = {}
        Model = self.env[model]
        for fname, field in fields.items():
            if field.get('type') != 'properties':
                continue

            definition_record = field['definition_record']
            definition_record_field = field['definition_record_field']

            # sudo(): user may lack access to property definition model
            target_model = Model.env[Model._fields[definition_record].comodel_name].sudo()
            domain_definition = [(definition_record_field, '!=', False)]
            # Depends of the records selected to avoid showing useless Properties
            if domain:
                self_subquery = Model.with_context(active_test=False)._search(domain)
                field_to_get = self_subquery.table[definition_record]
                domain_definition.append(('id', 'in', self_subquery.subselect(field_to_get)))

            definition_records = target_model.search_fetch(
                domain_definition, [definition_record_field, 'display_name'],
                order='id',  # Avoid complex order
            )

            for record in definition_records:
                for definition in record[definition_record_field]:
                    # definition = {
                    #     'name': 'aa34746a6851ee4e',
                    #     'string': 'Partner',
                    #     'type': 'many2one',
                    #     'comodel': 'test_orm.partner',
                    #     'default': [1337, 'Bob'],
                    # }
                    if (
                        definition['type'] == 'separator' or
                        (
                            definition['type'] in ('many2one', 'many2many')
                            and definition.get('comodel') not in Model.env
                        )
                    ):
                        continue
                    id_field = f"{fname}.{definition['name']}"
                    property_fields[id_field] = {
                        'type': definition['type'],
                        'string': Model.env._(
                            "%(property_string)s (%(parent_name)s)",
                            property_string=definition['string'], parent_name=record.display_name,
                        ),
                        'default_export_compatible': field['default_export_compatible'],
                    }
                    if definition['type'] in ('many2one', 'many2many'):
                        property_fields[id_field]['relation'] = definition['comodel']

        return property_fields

    @api.model
    def _get_fields_info(self, model, export_fields):
        """Resolve a list of technical export paths (e.g. ``partner_id/name``)
        into ``{'id', 'string', 'field_type', 'translate'}`` dicts whose ``string`` is the
        human readable label of the (possibly nested) field.
        """
        field_info = []
        fields = self.env[model].fields_get(
            attributes=[
                'type', 'string', 'required', 'relation_field', 'default_export_compatible',
                'relation', 'definition_record', 'definition_record_field', 'translate',
            ],
        )
        fields.update(self._get_property_fields(fields, model))
        if ".id" in export_fields:
            fields['.id'] = fields.get('id', {'string': 'ID'})

        # To make fields retrieval more efficient, fetch all sub-fields of a
        # given field at the same time. Because the order in the export list is
        # arbitrary, this requires ordering all sub-fields of a given field
        # together so they can be fetched at the same time
        #
        # Works the following way:
        # * sort the list of fields to export, the default sorting order will
        #   put the field itself (if present, for xmlid) and all of its
        #   sub-fields right after it
        # * then, group on: the first field of the path (which is the same for
        #   a field and for its subfields and the length of splitting on the
        #   first '/', which basically means grouping the field on one side and
        #   all of the subfields on the other. This way, we have the field (for
        #   the xmlid) with length 1, and all of the subfields with the same
        #   base but a length "flag" of 2
        # * if we have a normal field (length 1), just add it to the info
        #   mapping (with its string) as-is
        # * otherwise, recursively call _get_fields_info via _graft_subfields.
        #   all _graft_subfields does is take the result of _get_fields_info (on
        #   the field's model) and prepend the current base (current field),
        #   which rebuilds the whole sub-tree for the field
        #
        # result: because we're not fetching the fields_get for half the
        # database models, fetching a namelist with a dozen fields (including
        # relational data) falls from ~6s to ~300ms (on the leads model).
        # export lists with no sub-fields (e.g. import_compatible lists with
        # no o2m) are even more efficient (from the same 6s to ~170ms, as
        # there's a single fields_get to execute)
        for (base, length), subfields in itertools.groupby(
                sorted(export_fields),
                lambda field: (field.split('/', 1)[0], len(field.split('/', 1)))):
            subfields = list(subfields)
            if length == 2:
                # subfields is a seq of $base/*rest, and not loaded yet
                field_info.extend(
                    self._graft_subfields(
                        fields[base]['relation'], base, fields[base]['string'], subfields
                    ),
                )
            elif base in fields:
                field_dict = fields[base]
                field_info.append({
                    'id': base,
                    'string': field_dict['string'],
                    'field_type': field_dict['type'],
                    'translate': bool(field_dict.get('translate')),
                })

        indexes_dict = {fname: i for i, fname in enumerate(export_fields)}
        return sorted(field_info, key=lambda field_dict: indexes_dict[field_dict['id']])

    @api.model
    def _graft_subfields(self, model, prefix, prefix_string, fields):
        export_fields = [field.split('/', 1)[1] for field in fields]
        return (
            dict(
                field_info,
                id=f"{prefix}/{field_info['id']}",
                string=f"{prefix_string}/{field_info['string']}",
            )
            for field_info in self._get_fields_info(model, export_fields)
        )


class IrExportsLine(models.Model):
    _name = 'ir.exports.line'
    _description = 'Exports Line'
    _order = 'id'

    name = fields.Char(string='Field Name')
    export_id = fields.Many2one('ir.exports', string='Export', index=True, ondelete='cascade')
