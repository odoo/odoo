# -*- coding: utf-8 -*-
import datetime
from dateutil.relativedelta import relativedelta
import logging
import time
import uuid

from openerp import api, fields, models

_logger = logging.getLogger(__name__)


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
    payment_method_id = fields.Many2one('payment.method', 'Payment Method', help='If not set, the default payment method of the partner will be used.', domain="[('partner_id','=',partner_id)]")
    payment_mandatory = fields.Boolean('Automatic Payment', help='If set, payments will be made automatically and invoices will not be generated if payment attempts are unsuccessful.')
    # add tax calculation
    recurring_amount_tax = fields.Float('Taxes', compute="_amount_all")
    recurring_amount_total = fields.Float('Total', compute="_amount_all")

    closing_reason = fields.Char('Closing Reason')

    _sql_constraints = [
        ('uuid_uniq', 'unique (uuid)', """UUIDs (Universally Unique IDentifier) for account_analytic_account should be unique!"""),
    ]

    def _set_default_value_on_column(self, cr, column_name, context=None):
        # to avoid generating a single default uuid when installing the module,
        # we need to set the default row by row for this column
        if column_name == "uuid":
            _logger.debug("Table '%s': setting default value of new column %s to unique values for each row",
                          self._table, column_name)
            cr.execute("SELECT id FROM %s WHERE uuid IS NULL" % self._table)
            acc_ids = cr.dictfetchall()
            query_list = [{'id': acc_id['id'], 'uuid': str(uuid.uuid4())} for acc_id in acc_ids]
            query = 'UPDATE ' + self._table + ' SET uuid = %(uuid)s WHERE id = %(id)s;'
            cr._obj.executemany(query, query_list)
            cr.commit()

        else:
            super(account_analytic_account, self)._set_default_value_on_column(cr, column_name, context=context)

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
                val += line._amount_line_tax()
            account.recurring_amount_tax = cur.round(val)
            account.recurring_amount_total = account.recurring_amount_tax + account.recurring_total

    @api.depends('uuid')
    def _website_url(self):
        for account in self:
            if account.type == 'contract':
                account.website_url = '/account/contract/%s/%s' % (self.id, self.uuid)
            elif account.type == 'template':
                account.website_url = '/account/template/%s' % (self.id)

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
                account.recurring_inactive_lines = account.sudo().template_id.option_invoice_line_ids.filtered(lambda r: r.product_id not in [line.product_id for line in account.recurring_invoice_line_ids] and r.portal_access != 'invisible')

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

    # online payments

    # overwrite to add website sales team to recurring invocies
    @api.model
    def _prepare_invoice_data(self, contract):
        invoice = super(account_analytic_account, self)._prepare_invoice_data(contract)
        invoice.update({'team_id': self.env['ir.model.data'].get_object_reference('website', 'salesteam_website_sales')[1]})
        return invoice

    @api.one
    def _do_payment(self, payment_method, invoice, context=None):
        tx_obj = self.env['payment.transaction']
        reference = "CONTRACT-%s-%s" % (self.id, datetime.datetime.now().strftime('%y%m%d_%H%M%S'))
        values = {
            'amount': invoice.amount_total,
            'acquirer_id': payment_method.acquirer_id.id,
            'type': 'server2server',
            'currency_id': invoice.currency_id.id,
            'reference': reference,
            'partner_reference': payment_method.acquirer_ref,
            'partner_id': self.partner_id.id,
            'partner_country_id': self.partner_id.country_id.id,
            'invoice_id': invoice.id,
        }

        tx = tx_obj.create(values)

        baseurl = self.env['ir.config_parameter'].get_param('web.base.url')
        payment_secure = {'3d_secure': True,
                          'accept_url': baseurl + '/account/contract/%s/payment/%s/accept/' % (self.id, tx.id),
                          'decline_url': baseurl + '/account/contract/%s/payment/%s/decline/' % (self.id, tx.id),
                          'exception_url': baseurl + '/account/contract/%s/payment/%s/exception/' % (self.id, tx.id),
                          }
        tx.s2s_do_transaction(**payment_secure)
        return tx

    @api.one
    def reconcile_pending_transaction(self, tx, invoice):
        current_date = time.strftime('%Y-%m-%d')
        imd_res = self.env['ir.model.data']
        template_res = self.env['mail.template']
        if tx.state == 'done':
            invoice.signal_workflow('invoice_open')
            period_id = self.env['account.period'].find(current_date)
            journal = tx.acquirer_id.journal_id
            invoice.pay_and_reconcile(tx.amount, journal.default_credit_account_id.id,
                                      period_id.id, journal.id, False, False, False)
            next_date = datetime.datetime.strptime(self.recurring_next_date or current_date, "%Y-%m-%d")
            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
            invoicing_period = relativedelta(**{periods[self.recurring_rule_type]: self.recurring_interval})
            new_date = next_date + invoicing_period
            self.write({'recurring_next_date': new_date.strftime('%Y-%m-%d'), 'state': 'open', 'date': False})
        elif tx.state == 'error':
            invoice.action_cancel()
            invoice.unlink()

    @api.multi
    def _recurring_invoice(self, automatic=False):
        cr = self.env.cr
        invoice_ids = []
        current_date = time.strftime('%Y-%m-%d')
        imd_res = self.env['ir.model.data']
        template_res = self.env['mail.template']
        if len(self) > 0:
            contracts = self
        else:
            domain = [('recurring_next_date', '<=', current_date),
                      ('state', 'in', ['open', 'pending']),
                      ('type', '=', 'contract'),
                      ('contract_type', '=', 'subscription')]
            contracts = self.search(domain)
        if contracts:
            cr.execute('SELECT company_id, array_agg(id) as ids FROM account_analytic_account WHERE id IN %s GROUP BY company_id', (tuple(contracts.ids),))
            for company_id, ids in cr.fetchall():
                for contract in self.with_context(dict(self.env.context, company_id=company_id, force_company=company_id)).browse(ids):
                    # payment + invoice (only by cron)
                    if contract.template_id and contract.template_id.payment_mandatory and contract.recurring_total and automatic:
                        try:
                            payment_method = contract.payment_method_id
                            if not payment_method:
                                raise ValueError('No payment method for this contract')
                            invoice_values = self._prepare_invoice(contract)
                            new_invoice = self.env['account.invoice'].create(invoice_values)
                            new_invoice.check_tax_lines(self.env['account.invoice.tax'].compute(new_invoice))
                            tx = contract._do_payment(payment_method, new_invoice)
                            # commit change as soon as we try the payment so we have a trace somewhere
                            cr.commit()
                            if tx.state != 'done':
                                raise ValueError('Payment not validated by provider')
                            contract.reconcile_pending_transaction(tx, new_invoice)
                            _, template_id = imd_res.get_object_reference('sale_contract', 'email_payment_success')
                            email_context = self.env.context.copy()
                            email_context.update({
                                'payment_method': self.payment_method_id.name,
                                'renewed': True,
                                'total_amount': tx.amount,
                                'next_date': new_date.date(),
                                'previous_date': self.recurring_next_date,
                                'email_to': self.partner_id.email,
                                'code': self.code,
                                'currency': self.pricelist_id.currency_id.name,
                                'date_end': self.date,
                            })
                            _logger.debug("Sending Payment Confirmation Mail to %s for contract %s", self.partner_id.email, self.id)
                            template = template_res.browse(template_id)
                            template.with_context(email_context).send_mail(invoice.id)
                            msg_body = 'Automatic payment succeeded. Payment reference: %s; Amount: %s.' % (tx.reference, tx.amount)
                            self.message_post(body=msg_body)
                            cr.commit()
                        except Exception:
                            cr.rollback()
                            email_context = self.env.context.copy()
                            amount = contract.recurring_total
                            date_close = datetime.datetime.strptime(contract.recurring_next_date, "%Y-%m-%d") + relativedelta(days=15)
                            close_contract = current_date >= date_close.strftime('%Y-%m-%d')
                            email_context.update({
                                'payment_method': contract.payment_method_id.name if contract.payment_method_id else False,
                                'renewed': False,
                                'total_amount': amount,
                                'email_to': contract.partner_id.email,
                                'code': contract.code,
                                'currency': contract.pricelist_id.currency_id.name,
                                'date_end': contract.date,
                                'date_close': date_close.date()
                            })
                            _logger.exception('Fail to create recurring invoice for contract %s', contract.code)
                            if close_contract:
                                _, template_id = imd_res.get_object_reference('sale_contract', 'email_payment_close')
                                template = template_res.browse(template_id)
                                template.with_context(email_context).send_mail(contract.id)
                                _logger.debug("Sending Contract Closure Mail to %s for contract %s and closing contract", contract.partner_id.email, contract.id)
                                msg_body = 'Automatic payment failed after multiple attempts. Contract closed automatically.'
                                self.message_post(body=msg_body)
                            else:
                                _, template_id = imd_res.get_object_reference('sale_contract', 'email_payment_reminder')
                                if (datetime.datetime.today() - datetime.datetime.strptime(contract.recurring_next_date, '%Y-%m-%d')).days in [0, 3, 7, 14]:
                                    template = template_res.browse(template_id)
                                    template.with_context(email_context).send_mail(contract.id)
                                    _logger.debug("Sending Payment Failure Mail to %s for contract %s and setting contract to pending", contract.partner_id.email, contract.id)
                                    msg_body = 'Automatic payment failed. Contract set to "To Renew".'
                                    self.message_post(body=msg_body)
                            contract.write({'state': 'close' if close_contract else 'pending'})
                            cr.commit()
                    # invoice only
                    else:
                        try:
                            invoice_values = self._prepare_invoice(contract)
                            new_invoice = self.env['account.invoice'].create(invoice_values)
                            invoice_ids.append(new_invoice.id)
                            next_date = datetime.datetime.strptime(contract.recurring_next_date or current_date, "%Y-%m-%d")
                            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
                            invoicing_period = relativedelta(**{periods[contract.recurring_rule_type]: contract.recurring_interval})
                            new_date = next_date + invoicing_period
                            contract.write({'recurring_next_date': new_date.strftime('%Y-%m-%d')})
                            if automatic:
                                cr.commit()
                        except Exception:
                            if automatic:
                                cr.rollback()
                                _logger.exception('Fail to create recurring invoice for contract %s', contract.code)
                            else:
                                raise
        return invoice_ids


class account_analytic_invoice_line_option(models.Model):
    _inherit = "account.analytic.invoice.line"
    _name = "account.analytic.invoice.line.option"
    portal_access = fields.Selection(
        string='Portal Access',
        selection=[
            ('invisible', 'Invisible'),
            ('none', 'Restricted'),
            ('upgrade', 'Upgrade only'),
            ('both', 'Upgrade and Downgrade')],
        required=True,
        default='none',
        help="Restricted: The customer must ask a Sales Rep to add or remove this option\n"
             "Upgrade Only: The customer can add the option himself but must ask to remove it\n"
             "Upgrade and Downgrade: The customer can add or remove this option himself\n"
             "Invisible: The customer doesn't see the option; however it gets carried away when switching contract template")
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

    def _amount_line_tax(self):
        self.ensure_one()
        val = 0.0
        product = self.product_id
        product_tmp = product.sudo().product_tmpl_id
        for tax in product_tmp.taxes_id:
            fpos_obj = self.env['account.fiscal.position']
            partner = self.analytic_account_id.partner_id
            fpos_id = fpos_obj.get_fiscal_position(partner.company_id, partner.id)
            fpos = fpos_obj.browse(fpos_id)
            if fpos:
                tax = fpos.map_tax(tax)
            val += tax.compute_all(self.price_unit, self.quantity, product, partner)['taxes'][0].get('amount')
        return val
