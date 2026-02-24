# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class LabourQuotation(models.Model):
    _inherit = 'labour.quotation'
    _description = 'Labour Quotation'

    @api.model
    def _default_stage(self):
        st_ids = self.env['stage.master'].search([('draft', '=', True)])
        if st_ids:
            for st_id in st_ids:
                return st_id.id

    def change_state(self, context={}):
        if context.get('copy') == True:
            self.write({'state': 'confirm'})
        else:
            view_id = self.env.ref('pragtech_contracting.approval_wizard_form_view_contracting').id
            res = {
                'type': 'ir.actions.act_window',
                'res_model': 'approval.wizard',
                'multi': 'True',
                'target': 'new',
                'views': [[view_id, 'form']],
            }

            return res

    name = fields.Char('Order Reference', required=True, index=True, copy=False, default='New')
    origin = fields.Char('Source Document', copy=False,
                         help='Reference of the document that generated this purchase order request (e.g. a sale order or an internal procurement request)')

    date_order = fields.Datetime('Quotation Date', required=True, copy=False, default=fields.Datetime.now(),
                                 help='Depicts the date where the Quotation should be validated and converted into a purchase order.')
    partner_id = fields.Many2one('res.partner', string='Contractor', required=True, change_default=True, track_visibility='always')
    partner_ref = fields.Char('Vendor Reference', copy=False, help="Reference of the sales order or bid sent by the vendor. "
                                                                   "It's used to do the matching when you receive the "
                                                                   "products as this reference is usually written on the "
                                                                   "delivery order sent by your vendor.")
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.user.company_id.currency_id.id)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
    ], string='Status', copy=False, index=True, track_visibility='onchange', default='draft')
    order_line = fields.One2many('labour.quotation.line', 'order_id', string='Order Lines', copy=True)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, compute='_amount_all', track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, compute='_amount_all')
    valid_till = fields.Datetime('Valid Till')
    transport_amount = fields.Float('Transport Amount')
    loading_charges = fields.Float('Loading Charges')
    unloading_charges = fields.Float('Unloading Charges')
    other_charges = fields.Float('Other Charges')
    company_id = fields.Many2one('res.company', 'Company', index=1, default=lambda self: self.env.user.company_id.id)
    use_in_quotation = fields.Boolean('Use In Quotation')
    delivery_schedule = fields.Datetime(string='Delivery Schedule')
    host_name = fields.Char(string='Host Name')
    stage_id = fields.Many2one('stage.master', 'Stage', default=_default_stage, track_visibility='onchange')
    flag = fields.Boolean('Flag', default=False)
    mesge_ids = fields.One2many('mail.messages', 'res_id', string='Massage', domain=lambda self: [('model', '=', self._name)])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('labour.quotation') or '/'

            existing_stage = []
            st_id = self.env['stage.master'].search([('draft', '=', True)])
            msg_ids = {
                'date': datetime.now(),
                'from_stage': None,
                'to_stage': st_id.id,
                'remark': 'Created by ' + (self.env['res.users'].browse(self._context.get('uid'))).name,
                'model': 'labour.quotation'
            }
            existing_stage.append((0, 0, msg_ids))
            vals.update({'mesge_ids': existing_stage})

            return super(LabourQuotation, self).create(vals_list)

    @api.depends('order_line.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax

            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

    def _taxed_amount(self):
        return 1


class LabourQuotationLine(models.Model):
    _name = 'labour.quotation.line'
    _description = 'Labour Quotation Line'

    name = fields.Text(string='Description')
    labour_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1)
    date_planned = fields.Datetime(string='Scheduled Date', index=True)
    taxes_id = fields.Many2many('account.tax', 'labour_quot_line_tax_rel', 'labour_quot_line_id', 'tax_id', string='Taxes')
    labour_uom = fields.Many2one('uom.uom', string='Units', required=True)
    labour_id = fields.Many2one('labour.master', string='Labour', required=True)
    labour_category = fields.Many2one('labour.category', string='Labour Category', required=True)
    price_unit = fields.Float(string='Rate', required=True, digits=dp.get_precision('Product Price'))
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Discounted Rate', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Tax', store=True)

    work_class = fields.Many2one('labour.work.classification', 'Work Class')
    order_id = fields.Many2one('labour.quotation', string='Order Reference', index=True, required=True, ondelete='cascade')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account', domain=[('account_type', '=', 'normal')])
    company_id = fields.Many2one('res.company', related='order_id.company_id', string='Company', store=True)
    state = fields.Selection(related='order_id.state', stored=True, string='State')
    partner_id = fields.Many2one('res.partner', related='order_id.partner_id', string='Partner', store=True)
    currency_id = fields.Many2one(related='order_id.currency_id', store=True, string='Currency')
    currency_rate = fields.Float('Currency Rate')
    date_order = fields.Datetime(related='order_id.date_order', string='Order Date')
    brand_id = fields.Many2one('brand.brand', 'Brand')
    negotiated_rate = fields.Float('Negotiated Rate')
    credit_period = fields.Integer('Credit Period')
    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), default=0.0)
    vat_per = fields.Float('Vat(%)')
    vat_on_per = fields.Float('Vat on (%)')
    st_per = fields.Float('ST(%)')
    st_on_per = fields.Float('ST on (%)')
    retention = fields.Float('Retention(%)')
    payment_schedule = fields.Many2one('payment.schedule.template', 'Payment Schedule')

    taxed_amount = fields.Monetary(string='Taxed Amount', store=True, compute='_compute_amount')
    basic_amount = fields.Monetary(string='Basic Amount', store=True, compute='_compute_amount')
    net_rate = fields.Monetary(string='Net Rate', store=True, compute='_compute_amount')

    @api.onchange('labour_category')
    def onchange_labour_category(self):
        return {
            'domain': {
                'labour_id': [('category_id', '=', self.labour_category.id)]
            }
        }

    @api.onchange('labour_id')
    def onchange_labour_id(self):
        result = {}
        if not self.labour_id:
            return result

        # Reset date, price and quantity since _onchange_quantity will provide
        # default values
        self.date_planned = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.price_unit = self.labour_id.rate
        self.labour_uom = self.labour_id.unit_no
        self.work_class = self.labour_id.work_class_id.id

    @api.depends('labour_qty', 'discount', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        # Compute the amounts of the VQ line.
        for line in self:
            tax_amount = 0
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.taxes_id.compute_all(price, line.order_id.currency_id, line.labour_qty, product=line.labour_id, partner=line.order_id.partner_id)
            for tax in taxes['taxes']:
                tax_amount = tax_amount + tax['amount']

            basic_amount = line.price_unit * line.labour_qty
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
                'taxed_amount': tax_amount,
                'basic_amount': basic_amount,
                'net_rate': taxes['total_excluded'] + tax_amount,
            })

