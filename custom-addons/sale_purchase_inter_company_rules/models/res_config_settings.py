# -*- coding: utf-8 -*-
from odoo import models, fields, api
from .res_company import new_rule_type


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_validation = fields.Boolean(related='company_id.auto_validation', readonly=False)
    warehouse_id = fields.Many2one(
        related='company_id.warehouse_id',
        string='Warehouse For Purchase Orders',
        readonly=False,
        domain=lambda self: [('company_id', '=', self.env.company.id)])
    copy_lots_delivery = fields.Boolean(related='company_id.copy_lots_delivery', readonly=False)

    @api.onchange('rule_type')
    def onchange_rule_type(self):
        if self.rule_type not in new_rule_type.keys():
            self.auto_validation = False
            self.warehouse_id = False
            self.copy_lots_delivery = False
        elif self.rule_type != self.env.company.rule_type:
            warehouse_id = self.warehouse_id or self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
            self.warehouse_id = warehouse_id
            self.copy_lots_delivery = self.env.user.has_group('stock.group_production_lot')

    @api.depends('rule_type', 'auto_validation', 'warehouse_id', 'company_id')
    def _compute_intercompany_transaction_message(self):
        super()._compute_intercompany_transaction_message()
        for record in self:
            if record.rule_type in new_rule_type.keys():
                record.intercompany_transaction_message = record.company_id._intercompany_transaction_message_so_and_po(
                    record.rule_type, record.auto_validation, record.warehouse_id)
