from odoo import api, fields, models


class PortalListColumn(models.Model):
    """ Per-list customization of the portal document tables rendered through
    ``portal.portal_list_table``. Managed from the website builder (see the
    portal list column option). Each record either tweaks a built-in column
    (reorder / hide, ``field_name`` unset) or adds a new column for a model
    field (``field_name`` set). """
    _name = 'portal.list.column'
    _description = 'Portal List Column'
    _order = 'sequence, id'

    list_ref = fields.Char('List', required=True, index=True)
    name = fields.Char('Column', required=True)
    field_name = fields.Char('Field')
    sequence = fields.Integer('Sequence', default=10)
    show_in_portal = fields.Boolean('Show in Portal', default=True)

    _list_ref_name_uniq = models.Constraint(
        'unique(list_ref, name)',
        'A portal column with this name already exists for this list.',
    )

    # Field types a designer may add to a portal list. Not the relational ones,
    # even though portal.portal_list_cell renders them: their display name is
    # read as sudo, which would expose records the portal user cannot read.
    _PORTAL_FIELD_TYPES = ('char', 'text', 'html', 'date', 'datetime', 'integer', 'float', 'monetary', 'boolean')

    @api.model
    def get_available_fields(self, model_name):
        """ Return the fields of ``model_name`` that can be added as a portal
        column, as ``[{'id', 'display_name', 'type'}]`` (``id`` = field name).
        Consumed by the website builder column option. """
        # `fields_get` performs no access check of its own: only a user who may
        # configure the columns, and who may read the model, gets its fields.
        self.check_access('write')
        self.env[model_name].check_access('read')
        result = [
            {'id': fname, 'display_name': field.get('string') or fname, 'type': field['type']}
            for fname, field in self.env[model_name].fields_get().items()
            if field.get('type') in self._PORTAL_FIELD_TYPES and field.get('store') and not field.get('groups')
        ]
        result.sort(key=lambda record: record['display_name'])
        return result

    @api.model
    def replace_configuration(self, list_ref, columns):
        """Atomically replace the column configuration of a portal list."""
        self.check_access('write')
        self.search([('list_ref', '=', list_ref)]).unlink()
        if columns:
            self.create([
                {**column, 'list_ref': list_ref}
                for column in columns
            ])
