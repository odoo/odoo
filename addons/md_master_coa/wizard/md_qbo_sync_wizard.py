"""Phase 2 scaffold — QBO Sync Wizard.

This wizard will be fleshed out by the qbo_bridge module.
It is included here so the UI can reference it as a placeholder.
"""
from odoo import fields, models, _


class MdQboSyncWizard(models.TransientModel):
    _name = 'md.qbo.sync.wizard'
    _description = 'QBO Sync Wizard (Phase 2 Placeholder)'

    sync_direction = fields.Selection(
        [('push', 'Push to QBO'), ('pull', 'Pull from QBO'), ('both', 'Full 2-way Sync')],
        default='both', required=True)
    company_ids = fields.Many2many(
        'res.company', string='Companies',
        default=lambda self: self.env.companies)
    dry_run = fields.Boolean(
        'Dry Run', default=True,
        help='Preview what would be synced without actually sending data to QBO.')
    result_log = fields.Text('Result', readonly=True)

    def action_sync(self):
        self.result_log = _(
            'QBO Bridge module (qbo_bridge) is not installed.\n'
            'Install it to enable live QuickBooks Online synchronisation.\n\n'
            'Selected direction: %s\n'
            'Companies: %s\n'
            'Dry run: %s'
        ) % (
            self.sync_direction,
            ', '.join(self.company_ids.mapped('name')),
            self.dry_run,
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
