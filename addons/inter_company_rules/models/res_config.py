# -*- coding: utf-8 -*-
from openerp import models, fields, api

class inter_company_rules_configuration(models.TransientModel):

    _inherit = 'base.config.settings'

    company_id = fields.Many2one('res.company', string='Select Company',
        help='Select company to setup Inter company rules.')
    rule_type = fields.Selection([('so_and_po', 'SO and PO setting for inter company'),
        ('invoice_and_refunds', 'Create Invoice/Refunds when encoding invoice/refunds')],
        help='Select the type to setup inter company rules in selected company.')
    so_from_po = fields.Boolean(string='Create Sale Orders when buying to this company',
        help='Generate a Sale Order when a Purchase Order with this company as supplier is created.')
    po_from_so = fields.Boolean(string='Create Purchase Orders when selling to this company',
        help='Generate a Purchase Order when a Sale Order with this company as customer is created.')
    auto_validation = fields.Boolean(string='Sale/Purchase Orders Auto Validation',
        help='''When a Sale Order or a Purchase Order is created by a multi
            company rule for this company, it will automatically validate it.''')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse For Purchase Orders',
        help='Default value to set on Purchase Orders that will be created based on Sale Orders made to this company.')

    @api.onchange('rule_type')
    def onchange_rule_type(self):
        if self.rule_type == 'invoice_and_refunds':
            self.so_from_po = False
            self.po_from_so = False
            self.auto_validation = False

        elif self.rule_type == 'so_and_po':
            self.invoice_and_refunds = False

    @api.onchange('company_id')
    def onchange_company_id(self):
        if self.company_id:
            rule_type = False
            if self.company_id.so_from_po or self.company_id.po_from_so or self.company_id.auto_validation:
                rule_type = 'so_and_po'
            elif self.company_id.auto_generate_invoices:
                rule_type = 'invoice_and_refunds'

            self.rule_type = rule_type
            self.so_from_po = self.company_id.so_from_po
            self.po_from_so = self.company_id.po_from_so
            self.auto_validation = self.company_id.auto_validation
            self.warehouse_id = self.company_id.warehouse_id.id

    @api.multi
    def set_inter_company_configuration(self):
        if self.company_id:
            vals = {
                'so_from_po': self.so_from_po,
                'po_from_so': self.po_from_so,
                'auto_validation': self.auto_validation,
                'auto_generate_invoices': True if self.rule_type == 'invoice_and_refunds' else False,
                'warehouse_id': self.warehouse_id.id
            }
            self.company_id.write(vals)
