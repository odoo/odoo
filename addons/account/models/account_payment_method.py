# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import UserError


class AccountPaymentMethod(models.Model):
    _name = "account.payment.method"
    _description = "Payment Methods"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)  # For internal identification
    payment_type = fields.Selection(selection=[('inbound', 'Inbound'), ('outbound', 'Outbound')], required=True)

    _sql_constraints = [
        ('name_code_unique', 'unique (code, payment_type)', 'The combination code/payment type already exists!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        payment_methods = super().create(vals_list)
        methods_info = self._get_payment_method_information()
        for method in payment_methods:
            information = methods_info.get(method.code, {})

            if information.get('mode') == 'multi':
                method_domain = method._get_payment_method_domain()

                journals = self.env['account.journal'].search(method_domain)

                self.env['account.payment.method.line'].create([{
                    'name': method.name,
                    'payment_method_id': method.id,
                    'journal_id': journal.id
                } for journal in journals])
        return payment_methods

    def _get_payment_method_domain(self):
        """
        :return: The domain specyfying which journal can accomodate this payment method.
        """
        self.ensure_one()
        information = self._get_payment_method_information().get(self.code)

        currency_ids = information.get('currency_ids')
        country_id = information.get('country_id')
        default_domain = [('type', 'in', ('bank', 'cash'))]
        domains = [information.get('domain', default_domain)]

        if currency_ids:
            domains += [expression.OR([
                [('currency_id', '=', False), ('company_id.currency_id', 'in', currency_ids)],
                [('currency_id', 'in', currency_ids)]],
            )]

        if country_id:
            domains += [[('company_id.account_fiscal_country_id', '=', country_id)]]

        return expression.AND(domains)

    @api.model
    def _get_payment_method_information(self):
        """
        Contains details about how to initialize a payment method with the code x.
        The contained info are:
            mode: Either unique if we only want one of them at a single time (payment acquirers for example)
                   or multi if we want the method on each journal fitting the domain.
            domain: The domain defining the eligible journals.
            currency_id: The id of the currency necessary on the journal (or company) for it to be eligible.
            country_id: The id of the country needed on the company for it to be eligible.
            hidden: If set to true, the method will not be automatically added to the journal,
                    and will not be selectable by the user.
        """
        return {
            'manual': {'mode': 'multi', 'domain': [('type', 'in', ('bank', 'cash'))]},
        }

    @api.model
    def _get_sdd_payment_method_code(self):
        """
        TO OVERRIDE
        This hook will be used to return the list of sdd payment method codes
        """
        return []


class AccountPaymentMethodLine(models.Model):
    _name = "account.payment.method.line"
    _description = "Payment Methods"
    _order = 'sequence, id'

    # == Business fields ==
    name = fields.Char(compute='_compute_name', readonly=False, store=True)
    sequence = fields.Integer(default=10)
    payment_method_id = fields.Many2one(
        string='Payment Method',
        comodel_name='account.payment.method',
        domain="[('payment_type', '=?', payment_type), ('id', 'in', available_payment_method_ids)]",
        required=True
    )
    payment_account_id = fields.Many2one(
        comodel_name='account.account',
        check_company=True,
        copy=False,
        ondelete='restrict',
        domain=lambda self: "[('deprecated', '=', False), "
                            "('company_id', '=', company_id), "
                            "('user_type_id.type', 'not in', ('receivable', 'payable')), "
                            "'|', ('user_type_id', '=', %s), ('id', '=', parent.default_account_id)]"
                            % self.env.ref('account.data_account_type_current_assets').id
    )
    journal_id = fields.Many2one(comodel_name='account.journal', ondelete="cascade")

    # == Display purpose fields ==
    code = fields.Char(related='payment_method_id.code')
    payment_type = fields.Selection(related='payment_method_id.payment_type')
    company_id = fields.Many2one(related='journal_id.company_id')
    available_payment_method_ids = fields.Many2many(related='journal_id.available_payment_method_ids')

    @api.depends('payment_method_id.name')
    def _compute_name(self):
        for method in self:
            if not method.name:
                method.name = method.payment_method_id.name

    @api.constrains('name')
    def _ensure_unique_name_for_journal(self):
        self.flush(['name'])
        self._cr.execute('''
            SELECT apml.name, apm.payment_type
            FROM account_payment_method_line apml
            JOIN account_payment_method apm ON apml.payment_method_id = apm.id
            WHERE apml.journal_id IS NOT NULL
            GROUP BY apml.name, journal_id, apm.payment_type
            HAVING count(apml.id) > 1
        ''')
        res = self._cr.fetchall()
        if res:
            (name, payment_type) = res[0]
            raise UserError(_("You can't have two payment method lines of the same payment type (%s) "
                              "and with the same name (%s) on a single journal.", payment_type, name))

    def unlink(self):
        """
        Payment method lines which are used in a payment should not be deleted from the database,
        only the link betweend them and the journals must be broken.
        """
        unused_payment_method_lines = self
        for line in self:
            payment_count = self.env['account.payment'].search_count([('payment_method_line_id', '=', line.id)])
            if payment_count > 0:
                unused_payment_method_lines -= line

        (self - unused_payment_method_lines).write({'journal_id': False})

        return super(AccountPaymentMethodLine, unused_payment_method_lines).unlink()

    @api.model
    def _auto_toggle_account_to_reconcile(self, account_id):
        """ Automatically toggle the account to reconcile if allowed.

        :param account_id: The id of an account.account.
        """
        account = self.env['account.account'].browse(account_id)
        if not account.reconcile and account.internal_type != 'liquidity' and account.internal_group != 'off_balance':
            account.reconcile = True

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        for vals in vals_list:
            if vals.get('payment_account_id'):
                self._auto_toggle_account_to_reconcile(vals['payment_account_id'])
        return super().create(vals_list)

    def write(self, vals):
        # OVERRIDE
        if vals.get('payment_account_id'):
            self._auto_toggle_account_to_reconcile(vals['payment_account_id'])
        return super().write(vals)
