# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _



class PackAPP(models.Model):
    _name = 'custom.pack.app'
    _description = 'PC container Barcode Configuration.'

    name = fields.Char(string='Name', required=True,default=lambda self: _('New'))
    pc_container_status = fields.Selection([('release', 'Release'),
                                     ('occupied', 'Occupied'),],
                                    string='PC container Status', default='release')
    site_code_id = fields.Many2one('site.code.configuration', string='Site Code', store=True)
    pack_app_line_ids = fields.One2many(
        comodel_name='custom.pack.app.line',
        inverse_name='pack_app_line_id',
        string='Product Lines',
        tracking=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ], string='Status', readonly=True, tracking=True)


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
        self.state = 'in_progress'
        return {
            'name': _('Pack Bench Wizard'),
            'type': 'ir.actions.act_window',
            'res_model': 'custom.pack.app.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
        }



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
    tenant_code_id = fields.Many2one(related='picking_id.tenant_code_id', string='Tenant ID')
    site_code_id = fields.Many2one(related='picking_id.site_code_id', string='Site Code')



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
