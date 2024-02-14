# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ConfirmStockText(models.TransientModel):
    _name = 'confirm.stock.text'
    _description = 'Confirm Stock Text'

    pick_ids = fields.Many2many('stock.picking', 'stock_picking_text_rel')
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    confirmation_type = fields.Selection(related='company_id.confirmation_type', readonly=False)
    is_installed_stock_sms = fields.Boolean(compute='_compute_module_install', string="Is the Stock - SMS Module Installed")
    is_installed_whatsapp_stock = fields.Boolean(compute='_compute_module_install', string="Is the WhatsApp-Stock Module Installed")

    @api.depends('confirmation_type')
    def _compute_module_install(self):
        for record in self:
            record.is_installed_stock_sms = self.env['ir.module.module'].search([('name', '=', 'stock_sms'), ('state', '=', 'installed')])
            record.is_installed_whatsapp_stock = self.env['ir.module.module'].search([('name', '=', 'whatsapp_stock'), ('state', '=', 'installed')])

    def send_text(self):
        self.ensure_one()
        for company in self.pick_ids.company_id:
            company.sudo().write({'has_received_text_warning': True})
        pickings_to_validate = self.env['stock.picking'].browse(self.env.context.get('button_validate_picking_ids'))
        return pickings_to_validate.button_validate()

    def install_required_module(self):
        self.ensure_one()
        confirmation_type = self.confirmation_type
        for company in self.pick_ids.company_id:
            company.sudo().write({
                'text_confirmation': True,
                'confirmation_type': confirmation_type
            })

        # for Stock - SMS module
        if confirmation_type == 'sms' and not self.is_installed_stock_sms:
            module = self.env['ir.module.module'].search([('name', '=', 'stock_sms')])
            return module.button_immediate_install()
        # for WhatsApp-stock module
        if confirmation_type == 'whatsapp' and not self.is_installed_whatsapp_stock:
            module = self.env['ir.module.module'].search([('name', '=', 'whatsapp_stock')])
            return module.button_immediate_install()

    def dont_send_text(self):
        self.ensure_one()
        for company in self.pick_ids.company_id:
            company.sudo().write({
                'has_received_text_warning': True,
                'text_confirmation': False,
            })
        pickings_to_validate = self.env['stock.picking'].browse(self.env.context.get('button_validate_picking_ids'))
        return pickings_to_validate.button_validate()
