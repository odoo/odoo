# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

new_rule_type = {
    'sale': 'Synchronize Sales Order',
    'purchase': 'Synchronize Purchase Order',
    'sale_purchase': 'Synchronize Sales and Purchase Order',
}

class res_company(models.Model):
    _inherit = 'res.company'

    auto_validation = fields.Boolean(string="Automatic Validation")
    rule_type = fields.Selection(selection_add=list(new_rule_type.items()), string="Rule",
        help='Select the type to setup inter company rules in selected company.', default='not_synchronize')
    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse",
        help="Default value to set on Purchase(Sales) Orders that will be created based on Sale(Purchase) Orders made to this company")
    copy_lots_delivery = fields.Boolean(string="Copy Lots on Delivery Validation")

    def _intercompany_transaction_message_so_and_po(self, rule_type, auto_validation, warehouse_id):
        generated_object = {
            'sale': _('purchase order'),
            'purchase': _('sales order'),
            'sale_purchase': _('purchase/sales order'),
            False: ''
        }
        event_type = {
            'sale': _('sales order'),
            'purchase': _('purchase order'),
            'sale_purchase': _('sales/purchase order'),
            False: ''
        }
        text = {
            'validation': _('validated') if auto_validation else _('draft'),
            'generated_object': generated_object[rule_type],
            'warehouse': warehouse_id.sudo().display_name,
            'event_type': event_type[rule_type],
            'company': self.name,
        }
        if rule_type != 'sale':
            return _(
                'Generate a %(validation)s %(generated_object)s using '
                'warehouse %(warehouse)s when a company confirms a '
                '%(event_type)s for %(company)s.', **text)
        else:
            return _(
                'Generate a %(validation)s %(generated_object)s when a '
                'company confirms a %(event_type)s for %(company)s.', **text)

    @api.depends('rule_type', 'auto_validation', 'warehouse_id', 'name')
    def _compute_intercompany_transaction_message(self):
        super(res_company, self)._compute_intercompany_transaction_message()
        for record in self:
            if record.rule_type in new_rule_type.keys():
                record.intercompany_transaction_message = record._intercompany_transaction_message_so_and_po(record.rule_type, record.auto_validation, record.warehouse_id)

    @api.onchange('rule_type')
    def onchange_rule_type(self):
        if self.rule_type not in new_rule_type.keys():
            self.auto_validation = False
            self.warehouse_id = False
            self.copy_lots_delivery = False
        else:
            warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', self._origin.id)], limit=1)
            self.warehouse_id = warehouse_id
            self.copy_lots_delivery = self.env.user.has_group('stock.group_production_lot')
