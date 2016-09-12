import time
import re
from lxml import etree

from openerp import models, fields, api, tools, _
class sale_order(models.Model):
    _inherit = 'sale.order'
    version = fields.Integer(string=None,default=1,copy=True)
    crm_lead_id = fields.Many2one('crm.lead', string='Leads', index=True)
    is_copied = fields.Boolean(string='Is Copied?',default=False,copy=False)
    is_templete = fields.Boolean('Is Templete')
    profit_percentage = fields.Float(string='Profit Percentage (%)', default=10)
    total_confirm_sale = fields.Float(string='Total Sale Value')
    order_details = fields.Html('Quotation Details')
    templete_id = fields.Many2one('sale.order', 'Choose Templete', domain="[('is_templete', '=', True)]")
    state = fields.Selection(selection_add=[('early_payment', 'Early payment: Discount early payment')])
    paid_company_id = fields.Char(string='Mother Company',store=True, related='partner_id.mom_company_id.name', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approve'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sale Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')

    @api.one
    @api.constrains('profit_percentage')
    def _check_values(self):
        if self.profit_percentage < 0.0 or self.profit_percentage > 100.0:
            raise Warning(_('Values should in range 0 .. 100!.'))

    @api.multi
    def action_quotation_approve(self):
        self.write({'state': 'approve'})

    @api.onchange('templete_id')
    def _onchange_is_templete(self):
        if self.templete_id:
            templete = self.env['sale.order'].browse(self.templete_id.id)
            self.order_details = templete.order_details
    @api.multi
    def copy_button(self, default=None):
        default = dict(default or {})
        default.update({
            'name': self.name.split('_')[0] + "_" + str(self.version),
            'version': self.version + 1
        })
        ret = super(sale_order, self).copy(default)
        self.write({'is_copied': True})
        return {
            'name': _("Products to Process"),
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'sale.order',
            'res_id': ret.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': '[]',
            'flags' : {'initial_mode': 'edit'}
        }
    @api.multi
    def print_quotation(self):
        self.filtered(lambda s: s.state == 'approve').write({'state': 'sent'})
        return self.env['report'].get_action(self, 'sale.report_saleorder')

class crm_lead(models.Model):
    _inherit = 'crm.lead'
    sale_revenue = fields.Float('Revenue')
    reason_to_fail = fields.Text('Reason to fail')
    co_sales_ids = fields.Many2many('res.users', 'crm_lead_user_rel', 'lead_id', 'user_id', 'Co Sale man')


