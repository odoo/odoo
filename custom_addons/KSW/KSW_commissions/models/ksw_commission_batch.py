"""KSW Commission Batch — groups multiple ``ksw.commission.sheet`` records
for the same period so the accountant can review them as a unit and export
a single bank-transfer file covering all sheets in the batch.

Mirrors the ``hr.payslip.run`` concept from KSW_payroll:
  • One batch per period (but multiple allowed for different departments/sites)
  • State ``draft → confirmed → done``; only ``done`` sheets can be batched
  • Batch-level ``x_salary_bank_account_id`` as fallback for employees who
    have no individual bank account
  • ``action_open_export_wizard`` opens the unified bank-file export wizard
"""
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class KswCommissionBatch(models.Model):
    _name = 'ksw.commission.batch'
    _description = 'KSW Commission Batch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'period desc, id'

    name = fields.Char(required=True, default='New', copy=False, tracking=True)
    period = fields.Date(
        required=True, tracking=True,
        default=lambda s: fields.Date.context_today(s).replace(day=1),
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('closed', 'Closed')],
        default='draft', required=True, copy=False, tracking=True,
    )
    sheet_ids = fields.Many2many(
        'ksw.commission.sheet',
        'ksw_commission_batch_sheet_rel',
        'batch_id', 'sheet_id',
        string='Sheets',
        domain="[('state', '=', 'done'), "
               " ('period', '=', period)]",
    )
    # Fallback bank account for employees without their own
    x_salary_bank_account_id = fields.Many2one(
        'res.partner.bank',
        string='Default Paying Bank Account',
        help='Fallback for employees who have no personal '
             'Salary Paying Bank Account set.',
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id,
    )
    sheet_count = fields.Integer(compute='_compute_sheet_count')
    total_payable = fields.Monetary(
        compute='_compute_total_payable', store=True,
    )
    note = fields.Text()

    @api.depends('sheet_ids')
    def _compute_sheet_count(self):
        for rec in self:
            rec.sheet_count = len(rec.sheet_ids)

    @api.depends('sheet_ids.total_payable')
    def _compute_total_payable(self):
        for rec in self:
            rec.total_payable = sum(rec.sheet_ids.mapped('total_payable'))

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for v in vals_list:
            if not v.get('name') or v['name'] == 'New':
                v['name'] = seq.next_by_code('ksw.commission.batch') or 'New'
            if v.get('period'):
                d = fields.Date.to_date(v['period'])
                v['period'] = d.replace(day=1)
        return super().create(vals_list)

    def action_close(self):
        for rec in self:
            not_done = rec.sheet_ids.filtered(lambda s: s.state != 'done')
            if not_done:
                names = ', '.join(not_done.mapped('name'))
                raise UserError(_(
                    "All sheets must be in 'Done' state before closing the "
                    "batch. The following sheets are not done:\n%s", names,
                ))
            rec.write({'state': 'closed'})
            rec.message_post(
                body=Markup('<strong>Batch closed.</strong> %d sheets — '
                            'Total payable: %.2f') % (
                    len(rec.sheet_ids), rec.total_payable),
                subtype_xmlid='mail.mt_note',
            )

    def action_reset_to_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})

    def action_open_export_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Export Bank File'),
            'res_model': 'ksw.commission.bank.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_batch_id': self.id},
        }

    # ------------------------------------------------------------------
    # Grouping helper — mirrors hr.payslip.run._group_slips_by_bank_account
    # ------------------------------------------------------------------
    def _group_sheets_by_bank_account(self):
        """Group done commission sheets by the employee's paying bank.

        Resolution:
          1. Employee's ``x_salary_bank_account_id``
          2. Batch-level ``x_salary_bank_account_id``
          3. Falls into the empty-bank bucket (reported as error)
        """
        groups = {}
        bank_model = self.env['res.partner.bank']
        for sheet in self.sheet_ids:
            emp = sheet.employee_id.sudo()
            bank = (
                getattr(emp, 'x_salary_bank_account_id', bank_model)
                or self.x_salary_bank_account_id
                or bank_model
            )
            groups.setdefault(bank, self.env['ksw.commission.sheet'])
            groups[bank] |= sheet
        return groups

