# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .data_recycle_trash_model import DEFAULT_TRASH_RETENTION_DAYS

TRASH_RETENTION_PARAM = 'data_recycle.trash_retention_days'


class Data_RecycleTrashRecord(models.Model):
    _name = 'data_recycle.trash.record'
    _description = 'Trash Record'
    _order = 'delete_date desc, id desc'

    res_model_name = fields.Char(string='Model', required=True, index=True, readonly=True)
    record_id = fields.Char(string='Record ID', required=True, index=True, readonly=True)  # don't transform it to Many2oneReference
    record_name = fields.Char(string='Record Name', readonly=True)
    deleted_by = fields.Many2one(
        'res.users', string='Deleted By', readonly=True,
        default=lambda self: self.env.user,
    )
    delete_date = fields.Datetime(
        string='Deleted On', readonly=True, default=fields.Datetime.now,
    )
    field_data = fields.Json(string='Data', readonly=True)

    def write(self, vals):
        # Trash records are frozen: a snapshot that could be altered
        # afterwards would be worthless as a deletion trace. They can only be
        # created (on capture) and unlinked (on restore or garbage
        # collection), never modified, not even by the superuser.
        raise UserError(_('Trash records are frozen and cannot be modified.'))

    @api.depends('res_model_name', 'record_id', 'record_name')
    def _compute_display_name(self):
        for record in self:
            label = record.record_name or record.record_id
            record.display_name = f'{record.res_model_name},{label}'

    def _restore_vals(self):
        """ Return creation values rebuilt from the snapshot, skipping fields
        that can no longer be written: removed fields, many2one pointing to a
        deleted record or to a removed model. """
        self.ensure_one()
        model = self.env[self.res_model_name]
        vals = {}
        for name, value in (self.field_data or {}).items():
            field = model._fields.get(name)
            if field is None or not field.store or field.readonly:
                continue
            if field.type == 'many2one':
                if not value or field.comodel_name not in self.env \
                        or not self.env[field.comodel_name].browse(value).exists():
                    continue
            elif field.type == 'datetime' and value:
                value = datetime.fromisoformat(value)
            vals[name] = value
        return vals

    def action_restore(self):
        """ Recreate the deleted records from their snapshot, best effort:
        only the captured scalar fields still writable are restored, and the
        restored records get a new id. Restored entries leave the trash. """
        restored = []
        for trash in self:
            if trash.res_model_name not in self.env:
                raise UserError(_('The model %s no longer exists.', trash.res_model_name))
            restored.append(self.env[trash.res_model_name].create(trash._restore_vals()))
        self.unlink()
        if len(restored) == 1:
            record = restored[0]
            return {
                'type': 'ir.actions.act_window',
                'res_model': record._name,
                'res_id': record.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return True

    @api.autovacuum
    def _gc_trash_records(self):
        """ Remove trash records older than the retention configured per model,
        falling back to a global system parameter for models that no longer
        have a configuration. """
        now = fields.Datetime.now()
        default_retention = self.env['ir.config_parameter'].sudo().get_int(
            TRASH_RETENTION_PARAM, DEFAULT_TRASH_RETENTION_DAYS)

        # Per-model retention from active configurations.
        trash_models = self.env['data_recycle.trash.model'].sudo().with_context(active_test=False).search([])
        retention_by_model = {m.res_model_name: m.retention_days for m in trash_models}

        to_delete = self.browse()
        # Models still configured: use their own retention.
        for res_model_name, retention_days in retention_by_model.items():
            limit_date = now - timedelta(days=retention_days)
            to_delete |= self.search([
                ('res_model_name', '=', res_model_name),
                ('delete_date', '<', limit_date),
            ])
        # Orphan models (configuration removed): fall back to the global retention.
        limit_date = now - timedelta(days=default_retention)
        to_delete |= self.search([
            ('res_model_name', 'not in', list(retention_by_model.keys()) or [False]),
            ('delete_date', '<', limit_date),
        ])

        to_delete.unlink()
