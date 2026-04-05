from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MdAccountMapping(models.Model):
    """Maps a master COA account to a specific company's chart-of-accounts entry.

    Phase 1 : manual mapping via UI.
    Phase 2 : auto-populated by the QBO bridge sync job.
    """
    _name = 'md.account.mapping'
    _description = 'Master Account — Company Mapping'
    _order = 'company_id, master_account_id'
    _rec_name = 'display_name'

    master_account_id = fields.Many2one(
        'md.master.account', 'Master Account',
        required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(
        'res.company', 'Company / Branch',
        required=True, ondelete='cascade', index=True,
        default=lambda self: self.env.company)
    account_id = fields.Many2one(
        'account.account', 'Company Account',
        required=True, ondelete='cascade',
        domain="[('company_ids', 'in', [company_id])]")

    # QBO Phase-2 fields
    qbo_account_id = fields.Char(
        'QBO Account ID', copy=False,
        help='QuickBooks Online internal ID for this account in this company.')
    qbo_account_name = fields.Char('QBO Account Name', copy=False)
    qbo_account_type = fields.Char('QBO Account Type', copy=False)
    qbo_sub_account = fields.Boolean('QBO Sub-Account', default=False)
    is_active_qbo = fields.Boolean('Active in QBO', default=True)

    sync_state = fields.Selection(
        [
            ('not_synced', 'Not Synced'),
            ('synced', 'Synced'),
            ('conflict', 'Conflict'),
            ('error', 'Error'),
        ],
        string='Sync State', default='not_synced', tracking=True)
    last_sync = fields.Datetime('Last Sync', copy=False)
    sync_log = fields.Text('Sync Log', copy=False)

    # Convenience relational fields
    display_name = fields.Char(compute='_compute_display_name', store=True)
    master_code = fields.Char(related='master_account_id.code', store=True)
    master_category = fields.Selection(
        related='master_account_id.category', store=True)

    _sql_constraints = [
        ('unique_mapping', 'UNIQUE(master_account_id, company_id, account_id)',
         'A company account can only be mapped once per master account.'),
    ]

    @api.depends('master_account_id', 'company_id', 'account_id')
    def _compute_display_name(self):
        for rec in self:
            parts = []
            if rec.master_account_id:
                parts.append(rec.master_account_id.display_name)
            if rec.company_id:
                parts.append(rec.company_id.name)
            if rec.account_id:
                parts.append(rec.account_id.display_name)
            rec.display_name = ' → '.join(parts) if parts else _('New Mapping')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Backfill master_account_id on account.account for convenience
        for rec in records:
            if rec.account_id and not rec.account_id.master_account_id:
                rec.account_id.master_account_id = rec.master_account_id
        return records

    def action_sync_to_qbo(self):
        """Phase 2 placeholder — real logic lives in qbo_bridge."""
        for rec in self:
            rec.sync_state = 'not_synced'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('QBO Bridge not installed'),
                'message': _('Install the qbo_bridge module to enable live synchronisation.'),
                'type': 'warning',
                'sticky': False,
            },
        }
