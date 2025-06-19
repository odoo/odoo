# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PackAPP(models.Model):
    _name = 'custom.pack.app'
    _description = 'PC container Barcode Configuration.'

    name = fields.Char(string='Name', required=True,default=lambda self: _('New'))
    pc_container_status = fields.Selection([('release', 'Release'),
                                     ('occupied', 'Occupied'),],
                                    string='PC container Status', default='release')
    site_code_id = fields.Many2one('site.code.configuration', string='Site Code')
    pack_app_line_ids = fields.One2many(
        comodel_name='custom.pack.app.line',
        inverse_name='pack_app_line_id',
        string='Product Lines',
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ], default='draft',string='Status', readonly=True)
    automation_bulk_manual = fields.Selection([
        ('automation','Automation'),
        ('automation_bulk','Automation Bulk'),
        ('manual','Manual'),
    ], string='Automation Bulk Manual')
    pc_container_code_ids = fields.Many2many('pc.container.barcode.configuration', string='PC Totes')
    picking_ids = fields.Many2many('stock.picking', string='Pick Numbers', store=True)
    user_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, readonly=True)
    pack_bench_id = fields.Many2one(
        'pack.bench.configuration',
        string='Pack Bench',
        required=False,
        domain="[('site_code_id', '=', site_code_id)]",
        store=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.pack.app') or _('New')
        return super().create(vals_list)

    def scan_pc_container_code_pack(self):
        """
        Change the state of the Pack App to 'in_progress'
        and open the wizard to Pack an items .
        """
        for record in self:
            if not record.site_code_id:
                raise ValidationError(_("Please select a Site Code before proceeding to the Pack Screen."))
            if not record.pack_bench_id:
                raise ValidationError(_("Please select a Pack Bench before proceeding to the Pack Screen."))
            self.state = 'in_progress'
            return {
                'name': _('Pack Screen'),
                'type': 'ir.actions.act_window',
                'res_model': 'custom.pack.app.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'active_id': self.id},
            }

    def button_action_done(self):
        """
        Validate State from In Progress to Done when User hits this Done button
        """
        for order in self:
            order.state = 'done'



class PackAPPLine(models.Model):
    _name = 'custom.pack.app.line'
    _description = 'Pack App Line'
    _order = 'sequence, pack_app_line_id, id'

    name = fields.Char(string='Name')
    pack_app_line_id = fields.Many2one(
        comodel_name='custom.pack.app',
        string='Pack App',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string="Sequence")
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
    )
    quantity = fields.Float(string='Quantity')
    sku_code = fields.Char(related='product_id.default_code',string='SKU', store=True)
    display_type = fields.Selection(
        selection=[
            ('line_section', "Section"),
            ('line_note', "Note"),
        ],
        default=False)
    available_quantity = fields.Float(string='Available Quantity')
    remaining_quantity = fields.Float(string='Remaining Quantity')
    display_type_line_section = fields.Boolean(string='Display Type Line Section', default=False)
    picking_id = fields.Many2one('stock.picking', string='Picking Number')
    sale_order_id = fields.Many2one('sale.order', string='Sale Orders')
    tenant_code_id = fields.Many2one(related='picking_id.tenant_code_id', string='Tenant ID')
    site_code_id = fields.Many2one(related='picking_id.site_code_id', string='Site Code')
    serial_number = fields.Char(string='Serial Number')

    @api.model
    def create(self, vals_list):
        """
        Override the create method to handle special cases for certain
        display types. If the display_type indicates a section, the
        product_id and quantity are set to default values.
        """
        if vals_list.get('display_type'):
            vals_list.update(product_id=False, quantity=0)
        return super().create(vals_list)
