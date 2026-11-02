# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class QcInspection(models.Model):
    _name = 'od19.qc.inspection'
    _description = 'QC Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Inspection No.',
        default=lambda self: _('New'),
        copy=False, readonly=True, required=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True,
    )
    inspection_type = fields.Selection([
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing'),
        ('in_process', 'In-Process'),
    ], string='Inspection Type', default='incoming', required=True, tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string='Partner',
        help='Supplier for incoming, Customer for outgoing.',
    )
    picking_id = fields.Many2one(
        'stock.picking', string='Transfer',
        help='Linked stock picking for incoming/outgoing inspections.',
    )
    product_id = fields.Many2one(
        'product.product', string='Product',
        required=True, tracking=True,
    )
    lot_id = fields.Many2one(
        'stock.lot', string='Lot/Serial',
        domain="[('product_id', '=', product_id)]",
    )
    qty_tested = fields.Float(string='Quantity Tested', default=1.0, required=True)
    qty_accepted = fields.Float(string='Quantity Accepted', default=0.0)
    qty_rejected = fields.Float(string='Quantity Rejected', compute='_compute_qty_rejected', store=True)
    inspection_date = fields.Date(
        string='Inspection Date',
        default=fields.Date.context_today,
        required=True, tracking=True,
    )
    inspector_id = fields.Many2one(
        'res.users', string='Inspector',
        default=lambda self: self.env.user,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Result', compute='_compute_result', store=True)
    notes = fields.Text(string='Inspection Notes')
    nc_id = fields.Many2one(
        'od19.iso.nonconformity', string='Nonconformity',
        readonly=True, copy=False,
        help='Nonconformity created from a failed inspection.',
    )
    line_ids = fields.One2many(
        'od19.qc.inspection.line', 'inspection_id',
        string='Inspection Lines',
    )

    @api.constrains('qty_tested', 'qty_accepted')
    def _check_quantities(self):
        for rec in self:
            if rec.qty_tested < 0:
                raise UserError(_('Quantity Tested cannot be negative.'))
            if rec.qty_accepted < 0:
                raise UserError(_('Quantity Accepted cannot be negative.'))
            if rec.qty_accepted > rec.qty_tested:
                raise UserError(
                    _('Quantity Accepted cannot exceed Quantity Tested.')
                )

    @api.depends('qty_tested', 'qty_accepted')
    def _compute_qty_rejected(self):
        for rec in self:
            rec.qty_rejected = max(0.0, rec.qty_tested - rec.qty_accepted)

    @api.depends('qty_accepted', 'qty_tested', 'line_ids.result')
    def _compute_result(self):
        for rec in self:
            if rec.line_ids:
                failed_lines = rec.line_ids.filtered(lambda l: l.result == 'fail')
                rec.result = 'fail' if failed_lines else 'pass'
            else:
                rec.result = 'pass' if rec.qty_accepted >= rec.qty_tested else 'fail'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('od19.qc.inspection') or _('New')
        return super().create(vals_list)

    def action_start(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft inspections can be started.'))
            rec.state = 'in_progress'

    def action_pass(self):
        for rec in self:
            if rec.state not in ('draft', 'in_progress'):
                raise UserError(_('Cannot pass this inspection.'))
            if rec.result == 'fail':
                raise UserError(_('Inspection result is Fail. Cannot mark as Passed.'))
            rec.state = 'passed'

    def action_fail(self):
        for rec in self:
            if rec.state not in ('draft', 'in_progress'):
                raise UserError(_('Cannot fail this inspection.'))
            rec.state = 'failed'

    def action_cancel(self):
        for rec in self:
            if rec.state in ('passed', 'failed'):
                raise UserError(_('Cannot cancel a completed inspection.'))
            rec.state = 'cancelled'

    def action_create_nonconformity(self):
        """Create an ISO nonconformity (CAPA) from a failed inspection."""
        for rec in self:
            if rec.nc_id:
                continue
            if rec.result != 'fail':
                raise UserError(
                    _('Only failed inspections can raise a nonconformity.')
                )
            nc = self.env['od19.iso.nonconformity'].create({
                'title': _('QC Inspection %s failed') % rec.name,
                'severity': 'major',
                'source': {
                    'incoming': 'incoming',
                    'outgoing': 'final',
                    'in_process': 'process',
                }.get(rec.inspection_type, 'other'),
                'category': 'quality',
                'description': _(
                    'Product %(product)s: rejected %(rejected)s of '
                    '%(tested)s tested.',
                    product=rec.product_id.display_name,
                    rejected=rec.qty_rejected,
                    tested=rec.qty_tested,
                ),
                'partner_id': rec.partner_id.id,
                'responsible_id': rec.inspector_id.id,
            })
            rec.nc_id = nc.id


class QcInspectionLine(models.Model):
    _name = 'od19.qc.inspection.line'
    _description = 'QC Inspection Line'

    inspection_id = fields.Many2one(
        'od19.qc.inspection', string='Inspection',
        required=True, ondelete='cascade',
    )
    parameter = fields.Char(string='Parameter', required=True)
    expected_value = fields.Char(string='Expected Value')
    actual_value = fields.Char(string='Actual Value')
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Result', compute='_compute_result', store=True)
    notes = fields.Char(string='Notes')

    @api.depends('expected_value', 'actual_value')
    def _compute_result(self):
        for line in self:
            if not line.expected_value or not line.actual_value:
                line.result = False
            else:
                line.result = 'pass' if str(line.expected_value).strip().lower() == str(line.actual_value).strip().lower() else 'fail'
