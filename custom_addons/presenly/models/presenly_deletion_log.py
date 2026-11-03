from odoo import fields, models
from odoo.exceptions import UserError


class PresenlyDeletionLogMixin(models.AbstractModel):
    """Shared helpers for the Presenly deletion audit trail."""

    _name = 'presenly.deletion.log.mixin'
    _description = 'Presenly Deletion Audit Mixin'

    def _presenly_log_deletion(self, reason=''):
        for record in self:
            company = getattr(record, 'company_id', False)
            self.env['presenly.deletion.log'].sudo().create({
                'res_model': record._name,
                'res_id': record.id,
                'res_name': record.display_name,
                'deleted_by_id': self.env.user.id,
                'company_id': company.id if company else False,
                'reason': reason,
            })

    def _presenly_delete_snapshot(self):
        """Capture id/display_name/company before deletion so the audit entry
        can be written after ``super().unlink()`` succeeds."""
        snapshots = []
        for record in self:
            company = getattr(record, 'company_id', False)
            snapshots.append((
                record.id, record.display_name, company.id if company else False,
            ))
        return snapshots

    def _presenly_write_delete_log(self, snapshots, reason=''):
        for res_id, res_name, company_id in snapshots:
            self.env['presenly.deletion.log'].sudo().create({
                'res_model': self._name,
                'res_id': res_id,
                'res_name': res_name,
                'deleted_by_id': self.env.user.id,
                'company_id': company_id or False,
                'reason': reason,
            })

    def _presenly_purge_approval(self, keep_logs=True):
        """Remove the attached approval journey (steps cascade) of a request.

        ``presenly_approval_request_id`` uses ``ondelete='restrict'``, so the
        link must be detached before the journey can be removed. Decision
        records in ``presenly.approval.log`` are preserved by default as the
        immutable audit trail; pass ``keep_logs=False`` to purge them too.
        """
        for record in self:
            approval = record.presenly_approval_request_id
            if approval:
                workflow_write = getattr(
                    record, '_presenly_workflow_write', None
                )
                if workflow_write:
                    workflow_write({'presenly_approval_request_id': False})
                else:
                    record.sudo().with_context(
                        presenly_workflow=True
                    ).write({'presenly_approval_request_id': False})
                approval.sudo().with_context(
                    presenly_cascade_delete=True
                ).unlink()
                if not keep_logs:
                    self.env['presenly.approval.log'].sudo().search([
                        ('request_model', '=', record._name),
                        ('request_res_id', '=', record.id),
                    ]).unlink()


class PresenlyDeletionLog(models.Model):
    _name = 'presenly.deletion.log'
    _description = 'Presenly Deletion Audit Log'
    _order = 'create_date desc'

    res_model = fields.Char(required=True, index=True)
    res_id = fields.Integer(index=True)
    res_name = fields.Char(string='Record Name')
    deleted_by_id = fields.Many2one(
        'res.users', required=True, default=lambda self: self.env.user,
        string='Deleted By',
    )
    company_id = fields.Many2one('res.company', index=True)
    reason = fields.Char()
    deletion_date = fields.Datetime(
        default=fields.Datetime.now, required=True, index=True,
        string='Deletion Date',
    )

    def write(self, values):
        raise UserError('Deletion logs are append-only and cannot be modified.')

    def unlink(self):
        raise UserError('Deletion logs cannot be deleted.')