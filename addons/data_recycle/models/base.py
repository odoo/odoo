# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import api, fields, models

# Field types whose value is a JSON-serialisable scalar worth snapshotting.
_CAPTURED_FIELD_TYPES = {
    'boolean', 'integer', 'float', 'monetary', 'char', 'text', 'html',
    'date', 'datetime', 'selection', 'many2one',
}


class Base(models.AbstractModel):
    _inherit = 'base'

    def _trash_serialize(self, excluded_fields):
        """ Return a JSON-serialisable snapshot of this record's stored scalar
        fields. ``date``/``datetime`` are converted to ISO strings and
        ``many2one`` is stored as its id. """
        self.ensure_one()
        data = {}
        for name, field in self._fields.items():
            if name in excluded_fields:
                continue
            if not field.store or field.type not in _CAPTURED_FIELD_TYPES:
                continue
            value = self[name]
            if field.type == 'many2one':
                value = value.id or False
            elif field.type in ('date', 'datetime') and value:
                value = value.isoformat()
            data[name] = value
        return data

    @api.ondelete(at_uninstall=False)
    def _unlink_capture_trash(self):
        if self._transient:
            return
        TrashModel = self.env['data_recycle.trash.model'].sudo()
        # check never-tracked models first: their deletion must not touch the
        # tracked models ormcache (see _unlink_invalidate_tracked_models_cache)
        if self._name in TrashModel._get_never_tracked():
            return
        if self._name in TrashModel._get_tracked_models():
            self._trash_capture()

    def _trash_capture(self):
        """ Create a ``data_recycle.trash.record`` snapshot for each record
        about to be deleted and matching the configured filter, if any. Runs
        as sudo so any user can delete a tracked record even without access
        to ``data_recycle.trash.record`` or to group-restricted fields of the
        deleted record. """
        TrashModel = self.env['data_recycle.trash.model'].sudo()
        records = self.sudo()
        domain = ast.literal_eval(TrashModel._get_domain(self._name))
        if domain:
            records = records.filtered_domain(domain)
        if not records:
            return
        excluded_fields = TrashModel._get_excluded_fields(self._name)
        now = fields.Datetime.now()
        uid = self.env.user.id
        vals_list = []
        for record in records:
            vals_list.append({
                'res_model_name': record._name,
                'record_id': str(record.id),
                'record_name': record.display_name,
                'deleted_by': uid,
                'delete_date': now,
                'field_data': record._trash_serialize(excluded_fields),
            })
        if vals_list:
            self.env['data_recycle.trash.record'].sudo().create(vals_list)
