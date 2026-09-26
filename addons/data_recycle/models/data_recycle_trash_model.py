# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError

DEFAULT_TRASH_RETENTION_DAYS = 30


class Data_RecycleTrashModel(models.Model):
    _name = 'data_recycle.trash.model'
    _description = 'Trash Model'
    _rec_name = 'res_model_id'

    res_model_id = fields.Many2one(
        'ir.model', string='Model', required=True, ondelete='cascade',
        domain=lambda self: [('transient', '=', False), ('abstract', '=', False), ('model', 'not in', list(self._get_never_tracked()))],
        help="Model whose deletions should be recorded in the trash.",
    )
    res_model_name = fields.Char(
        related='res_model_id.model', string='Model Name', store=True, index=True,
    )
    retention_days = fields.Integer(
        string='Retention (days)', default=DEFAULT_TRASH_RETENTION_DAYS, required=True,
        help="Trash records of this model older than this number of days are "
             "removed by the scheduled action.",
    )
    domain = fields.Char(
        string='Filter', compute='_compute_domain', readonly=False, store=True,
        help="Only deleted records matching this filter are captured in the "
             "trash. Leave empty to capture all of them.",
    )
    excluded_field_ids = fields.Many2many(
        'ir.model.fields', string='Excluded Fields',
        domain="[('model_id', '=', res_model_id)]",
        help="Fields that should not be stored in the snapshot (e.g. sensitive data).",
    )
    active = fields.Boolean(default=True)
    trash_record_count = fields.Integer(
        'Deleted Records', compute='_compute_trash_record_count')

    _res_model_uniq = models.Constraint(
        'UNIQUE(res_model_id)',
        'A trash configuration already exists for this model.',
    )

    @api.depends('res_model_id')
    def _compute_domain(self):
        self.domain = '[]'

    @api.constrains('res_model_id')
    def _check_res_model_id(self):
        never_tracked = self._get_never_tracked()
        for trash_model in self:
            if trash_model.res_model_id.model in never_tracked:
                raise ValidationError(self.env._(
                    "Deletions of model %s cannot be tracked in the trash.",
                    trash_model.res_model_id.model,
                ))

    def _compute_trash_record_count(self):
        count_data = self.env['data_recycle.trash.record']._read_group(
            [('res_model_name', 'in', [m.res_model_name for m in self])],
            ['res_model_name'],
            ['__count'])
        counts = dict(count_data)
        for trash_model in self:
            trash_model.trash_record_count = counts.get(trash_model.res_model_name, 0)

    def open_trash_records(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('data_recycle.action_data_recycle_trash_record')
        action['domain'] = [('res_model_name', '=', self.res_model_name)]
        action['context'] = {}
        return action

    @api.model
    def _get_never_tracked(self):
        """ Return the set of model names that must never be tracked,
        regardless of configuration, to avoid recursion and pointless churn:
        trash records themselves, the trash configuration (whose deletion
        must not repopulate the tracked models cache it just invalidated),
        and the recycle work-queue entries that the recycle crons mass-unlink
        on every run. These models are not selectable in the configuration
        (see the domain of ``res_model_id`` and ``_check_res_model_id``).
        Meant to be extended by overriding modules. """
        return {
            'data_recycle.trash.record',
            'data_recycle.trash.model',
            'data_recycle.record',
            # relational plumbing, mass-deleted by mail flows (unsubscribe,
            # cascade with the followed record): capturing it is pointless
            # churn and restoring it would create dangling followers
            'mail.followers',
        }

    @api.model
    @api.ormcache(cache='stable')
    def _get_tracked_models(self):
        """ Return the frozenset of model names whose deletions are recorded.

        Cached so that an ``unlink()`` on a non-tracked model performs no SQL.
        Cached in the 'stable' group: it is read on every unlink of every
        model, so it must survive the frequent invalidations of the 'default'
        group. Invalidated on create/write/unlink below.
        """
        return frozenset(self.sudo().search([]).mapped('res_model_name')) - self._get_never_tracked()

    @api.model
    @api.ormcache('res_model_name', cache='stable')
    def _get_excluded_fields(self, res_model_name):
        """ Return the set of field names excluded from the snapshot for a
        given tracked model. """
        trash_model = self.sudo().search([('res_model_name', '=', res_model_name)], limit=1)
        return frozenset(trash_model.excluded_field_ids.mapped('name'))

    @api.model
    @api.ormcache('res_model_name', cache='stable')
    def _get_domain(self, res_model_name):
        """ Return the filter (as a string) restricting which deleted records
        of a given tracked model are captured. """
        trash_model = self.sudo().search([('res_model_name', '=', res_model_name)], limit=1)
        return trash_model.domain or '[]'

    @api.model
    def _invalidate_tracked_models_cache(self):
        # the ORM cache can only be invalidated by group; 'stable' is the
        # narrowest group containing the caches above
        self.env.transaction.invalidate_ormcache('stable')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self._invalidate_tracked_models_cache()
        return records

    def write(self, vals):
        res = super().write(vals)
        # 'active', 'res_model_id', 'domain' and 'excluded_field_ids' all affect capture
        self._invalidate_tracked_models_cache()
        return res

    @api.ondelete(at_uninstall=True)
    def _unlink_invalidate_tracked_models_cache(self):
        # this runs before the rows are actually deleted, but nothing can
        # repopulate the cache in between: the capture hook skips this model
        # (see _get_never_tracked)
        self._invalidate_tracked_models_cache()
