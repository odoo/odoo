# -*- coding: utf-8 -*-
import datetime
from dateutil.relativedelta import relativedelta
import uuid

from openerp import api, fields, models


class account_analytic_account(models.Model):
    _inherit = "account.analytic.account"
    _name = "account.analytic.account"

    uuid = fields.Char('Account UUID', default=lambda s: uuid.uuid4(), copy=False, required=True)
    website_url = fields.Char('Website URL', compute='_website_url', help='The full URL to access the document through the website.')
    recurring_mandatory_lines = fields.Many2many('account.analytic.invoice.line', compute="_compute_options")
    recurring_option_lines = fields.Many2many('account.analytic.invoice.line', compute="_compute_options")
    recurring_inactive_lines = fields.Many2many('account.analytic.invoice.line.option', compute="_compute_options")
    recurring_custom_lines = fields.Many2many('account.analytic.invoice.line', compute="_compute_options")
    user_closable = fields.Boolean(string="Closable by customer", help="If checked, the user will be able to close his account from the frontend")
    option_invoice_line_ids = fields.One2many('account.analytic.invoice.line.option', inverse_name='analytic_account_id', string='Optional Lines', copy=True)
    # add tax calculation, but probably incomplete (fiscal position? how does that work?)
    recurring_amount_tax = fields.Float('Taxes', compute="_amount_all")
    recurring_amount_total = fields.Float('Total', compute="_amount_all")

    @api.depends('recurring_invoice_line_ids')
    def _amount_all(self):
        for account in self:
            res = {
                'recurring_amount_tax': 0.0,
                'recurring_amount_total': 0.0,
            }
            val = val1 = 0.0
            cur = account.pricelist_id.currency_id
            for line in account.recurring_invoice_line_ids:
                val1 += line.price_subtotal
                val += line._amount_line_tax()[0]
            account.recurring_amount_tax = cur.round(val)
            account.recurring_amount_total = account.recurring_amount_tax + account.recurring_total

    @api.depends('uuid')
    def _website_url(self):
        for account in self:
            account.website_url = '/account/contract/%s/%s' % (self.id, self.uuid)

    @api.multi
    def open_website_url(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.website_url,
            'target': 'self',
        }

    def add_option(self, option_id):
        option = self.env['account.analytic.invoice.line.option'].browse(option_id)
        if option not in self.template_id.option_invoice_line_ids:
            return False
        values = {
            'product_id': option.product_id.id,
            'analytic_account_id': self.id,
            'name': option.name,
            'quantity': option.quantity,
            'uom_id': option.uom_id.id,
            'price_unit': option.price_unit,
            }
        self.write({'recurring_invoice_line_ids': [(0, 0, values)]})
        return True

    def remove_option(self, option_line_id):
        opt_line = self.env['account.analytic.invoice.line.option'].browse(option_line_id)
        if not self.template_id or opt_line not in self.template_id.option_invoice_line_ids:
            return False
        for line in self.recurring_invoice_line_ids:
            if opt_line.product_id == line.product_id:
                self.write({'recurring_invoice_line_ids': [(2, line.id)]})
                return True
        return False

    def change_subscription(self, new_template_id):
        """Change the template of a contract with contract_type 'subscription'
        - add the recurring_invoice_line_ids linked to the new template
        - remove the recurring_invoice_line_ids linked to the current template
        - remove lines that are not in the new template option_invoice_line_ids
        - adapt price of lines that are in the option_invoice_line_ids of both templates
        - other invoicing lines are left unchanged"""
        if self.contract_type != 'subscription':
            return False
        rec_lines_to_remove = []
        rec_lines_to_add = []
        rec_lines_to_modify = []
        new_template = self.browse(new_template_id)
        new_options = {line.product_id: line.price_unit for line in new_template.option_invoice_line_ids}
        # add new mandatory lines
        rec_lines_to_add = [(0, 0, {
            'product_id': tmp_line.product_id.id,
            'uom_id': tmp_line.uom_id.id,
            'name': tmp_line.name,
            'quantity': tmp_line.quantity,
            'price_unit': tmp_line.price_unit,
            'analytic_account_id': self.id,
            }) for tmp_line in new_template.recurring_invoice_line_ids]
        # remove old mandatory line
        for line in self.recurring_invoice_line_ids:
            if line.product_id in [tmp_line.product_id for tmp_line in self.template_id.recurring_invoice_line_ids]:
                rec_lines_to_remove.append((2, line.id))
            if line.product_id in [tmp_option.product_id for tmp_option in self.template_id.option_invoice_line_ids]:
                # remove options in the old template that are not in the new one (i.e. options that do not apply anymore)
                if line.product_id not in new_options:
                    rec_lines_to_remove.append((2, line.id))
                # adapt prices of options
                else:
                    rec_lines_to_modify.append((1, line.id, {
                        'price_unit': new_options.get(line.product_id)
                    }))
        values = {
            'recurring_invoice_line_ids': rec_lines_to_add + rec_lines_to_modify + rec_lines_to_remove,
            'recurring_rule_type': new_template.recurring_rule_type
            }
        self.sudo().write(self.on_change_template(new_template_id).get('value', dict()))
        self.sudo().write(values)
        self.template_id = new_template

    def _compute_options(self):
        """ Set fields with filter options:
            - recurring_mandatory_lines = all the recurring lines that are recurring lines on the template
            - recurring_option_lines = all the contract lines that are option lines on the template
            - recurring_custom_lines = all the recurring lines that are not part of the template
            - recurring_inactive_lines = all the template_id's options that are not set on the contract
        """
        for account in self:
            if account.type == 'contract' and account.template_id:
                account.recurring_mandatory_lines = account.recurring_invoice_line_ids.filtered(lambda r: r.product_id in [inv_line.product_id for inv_line in account.sudo().template_id.recurring_invoice_line_ids])
                account.recurring_option_lines = account.recurring_invoice_line_ids.filtered(lambda r: r.product_id in [line.product_id for line in account.sudo().template_id.option_invoice_line_ids])
                account.recurring_custom_lines = account.recurring_invoice_line_ids.filtered(lambda r: r.product_id not in [opt_line.product_id for opt_line in account.sudo().template_id.option_invoice_line_ids]+[inv_line.product_id for inv_line in account.sudo().template_id.recurring_invoice_line_ids])
                account.recurring_inactive_lines = account.sudo().template_id.option_invoice_line_ids.filtered(lambda r: r.product_id not in [line.product_id for line in account.recurring_invoice_line_ids])

    def get_line_price(self, product_id):
        """ Get the price of an invoice line (recurrent or option for templates) via its product_id """
        if self.type == "contract":
            return self.recurring_invoice_line_ids.filtered(lambda r: r.product_id.id == product_id).price_unit
        if self.type == "template":
            if product_id in [line.product_id.id for line in self.recurring_invoice_line_ids]:
                return self.recurring_invoice_line_ids.filtered(lambda r: r.product_id.id == product_id).price_unit
            elif product_id in [line.product_id.id for line in self.option_invoice_line_ids]:
                return self.option_invoice_line_ids.filtered(lambda r: r.product_id.id == product_id).price_unit
        return False

    def partial_invoice_line(self, sale_order, option_line, refund=False):
        """ Add an invoice line on the sale order for the specified option and add a discount
        to take the partial recurring period into account """
        order_line_obj = self.env['sale.order.line']
        if option_line.product_id in [line.product_id for line in sale_order.order_line]:
            return True
        values = {
            'order_id': sale_order.id,
            'product_id': option_line.product_id.id,
            'product_uom_qty': option_line.quantity,
            'product_uom': option_line.uom_id.id,
            'discount': (1-self.partial_recurring_invoice_ratio())*100,
            'price_unit': option_line.price_unit,
            'force_price': True,
            'name': option_line.name,
        }
        return order_line_obj.create(values)

    def partial_recurring_invoice_ratio(self):
        """Computes the ratio of the amount of time remaining in the current invoicing period
        over the total length of said invoicing period"""
        today = datetime.date.today()
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        invoicing_period = relativedelta(**{periods[self.recurring_rule_type]: self.recurring_interval})
        recurring_next_invoice = fields.Date.from_string(self.recurring_next_date)
        recurring_last_invoice = recurring_next_invoice - invoicing_period
        time_to_invoice = recurring_next_invoice - today
        ratio = float(time_to_invoice.days)/float((recurring_next_invoice-recurring_last_invoice).days)
        return ratio

    # overwrite to add website sales team to recurring invocies
    def _prepare_invoice_data(self, cr, uid, contract, context=None):
        invoice = super(account_analytic_account, self)._prepare_invoice_data(cr, uid, contract, context=context)
        invoice.update({'team_id': self.pool['ir.model.data'].get_object_reference(cr, uid, 'website', 'salesteam_website_sales')[1]})
        return invoice


class account_analytic_invoice_line_option(models.Model):
    _inherit = "account.analytic.invoice.line"
    _name = "account.analytic.invoice.line.option"
    portal_access = fields.Selection(
        string='Portal Access',
        selection=[
            ('none', 'Restricted'),
            ('upgrade', 'Upgrade only'),
            ('both', 'Upgrade and Downgrade')],
        required=True,
        default='none',
        help="""Restricted: The user must ask a Sales Rep to add or remove this option
Upgrade Only: The user can add the option himself but must ask to remove it
Upgrade and Downgrade: The user can add or remove this option himself""")
    is_authorized = fields.Boolean(compute="_compute_is_authorized", search="_search_is_authorized")

    def _compute_is_authorized(self):
        for option in self:
            option.is_authorized = bool(self.env['account.analytic.account'].search([('template_id', '=', option.analytic_account_id.id)]))

    def _search_is_authorized(self, operator, value):
        if operator != '=':
            return []
        ids = []
        for option in self.search([]):
            if self.env['account.analytic.account'].search([('template_id', '=', option.analytic_account_id.id)]):
                ids.append(option.id)
        return [('id', 'in', ids)]


class account_analytic_invoice_line(models.Model):
    _inherit = "account.analytic.invoice.line"
    _name = "account.analytic.invoice.line"

    def get_template_option_line(self):
        """ Return the account.analytic.invoice.line.option which has the same product_id as
        the invoice line"""
        if not self.analytic_account_id and not self.analytic_account_id.template_id:
            return False
        template = self.analytic_account_id.template_id
        return template.sudo().option_invoice_line_ids.filtered(lambda r: r.product_id == self.product_id)

    @api.one
    def _amount_line_tax(self):
        val = 0.0
        product = self.product_id
        product_templ = product.sudo().product_tmpl_id
        for tax in product_templ.taxes_id:
            val += tax.compute_all(self.price_unit, self.quantity, product, self.analytic_account_id.partner_id)['taxes'][0].get('amount')
        return val
