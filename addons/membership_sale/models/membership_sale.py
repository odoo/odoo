# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp import tools, models, fields, api


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    membership_start_date = fields.Date(
        string='Membership Start Date', default=fields.date.today(), help='Date from which membership becomes active.')

    def _prepare_membership_line(self, line):
        end_date = (datetime.strptime(line.membership_start_date, tools.DEFAULT_SERVER_DATE_FORMAT).date()) + \
            relativedelta(months=line.product_id.membership_duration, days=-1)
        return {
            'partner': line.order_partner_id.id,
            'membership_id': line.product_id.id,
            'member_price': line.price_unit,
            'date_from': line.membership_start_date,
            'date_to': end_date,
            'state': 'waiting',
            'sale_order_line_id': line.id
        }

    @api.multi
    def button_confirm(self):
        res = super(sale_order_line, self).button_confirm()
        for line in self.filtered(lambda line: line.product_id.membership):
            if line.price_unit > 0 and self.order_partner_id.free_member:
                self.env['res.partner'].search(
                [('id', '=', self.order_partner_id.id)]).write({'free_member': False})
            self.env['membership.membership_line'].create(
                self._prepare_membership_line(line))
        return res

    @api.multi
    def invoice_line_create(self):
        res = super(sale_order_line, self).invoice_line_create()
        for line_id in self.filtered(lambda line_id: line_id and line_id.invoice_lines):
            self.env['membership.membership_line'].search([('sale_order_line_id', '=', line_id.id)]).write(
                {'date': fields.date.today(), 'account_invoice_line': line_id.invoice_lines.id})
        return res


class membership_line(models.Model):

    '''Membership line'''
    _inherit = 'membership.membership_line'

    sale_order_line_id = fields.Many2one(
        'sale.order.line', 'Sale Order line', readonly=True)
    sale_order_id = fields.Many2one(
        string='Sale Order', related='sale_order_line_id.order_id')


class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'

    @api.model
    def _prepare_domain_invoice_membership(self, line):
        domain = super(
            account_invoice_line, self)._prepare_domain_invoice_membership(line)
        return ['|', ('sale_order_line_id', '!=', False)] + domain


class Partner(models.Model):

    '''Partner'''
    _inherit = 'res.partner'

    membership_state = fields.Selection(
        help='It indicates the membership state.\n'
        '-Non Member: A partner who has not applied for any membership or applied for the membership and whose invoice is going to be created.\n'
        '-Cancelled Member: A member who has cancelled his membership.\n'
        '-Old Member: A member whose membership date has expired.\n'
        '-Waiting Member: A member whose invoice has been created.\n'
        '-Invoiced Member: A member whose invoice has been validate.\n'
        '-Paying member: A member who has paid the membership fee.')
