# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class AccountPaymentMethod(models.Model):
    _name = 'account.payment.method'
    _description = "Payment Methods"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)  # For internal identification
    payment_type = fields.Selection(selection=[('inbound', 'Inbound'), ('outbound', 'Outbound')], required=True)

    _name_code_unique = models.Constraint(
        'unique (code, payment_type)',
        'The combination code/payment type already exists!',
    )

    @api.model_create_multi
    def create(self, vals_list):
        payment_methods = super().create(vals_list)
        methods_info = self._get_payment_method_information()
        return self._auto_link_payment_methods(payment_methods, methods_info)

    def _auto_link_payment_methods(self, payment_methods, methods_info):
        # This method was extracted from create so it can be overriden in the upgrade script.
        # In said script we can then allow for a custom behavior for the payment.method.line on the journals.
        for method in payment_methods:
            information = methods_info.get(method.code, {})
            if information.get('mode') == 'multi':
                method_domain = method._get_payment_method_domain(method.code)
                journals = self.env['account.journal'].search(method_domain)
                self.env['account.payment.method.line'].create([{
                    'name': method.name,
                    'payment_method_id': method.id,
                    'journal_id': journal.id
                } for journal in journals])
        return payment_methods

    @api.model
    def _get_payment_method_domain(self, code, with_currency=True, with_country=True):
        """
        :param code: string of the payment method line code to check.
        :param with_currency: if False (default True), ignore the currency_id domain if it exists.
        :return: The domain specifying which journal can accommodate this payment method.
        """
        if not code:
            return Domain.TRUE
        information = self._get_payment_method_information().get(code)
        journal_types = information.get('type', ('bank', 'cash', 'credit'))
        domain = Domain('type', 'in', journal_types)

        if with_currency and (currency_ids := information.get('currency_ids')):
            domain &= (
                Domain('currency_id', '=', False) & Domain('company_id.currency_id', 'in', currency_ids)
            ) | Domain('currency_id', 'in', currency_ids)

        if with_country and (country_id := information.get('country_id')):
            domain &= Domain('company_id.account_fiscal_country_id', '=', country_id)

        return domain

    @api.model
    def _get_payment_method_information(self):
        """
        Contains details about how to initialize a payment method with the code x.
        The contained info are:

        - ``mode``: One of the following:
          "unique" if the method cannot be used twice on the same company,
          "electronic" if the method cannot be used twice on the same company for the same 'payment_provider_id',
          "multi" if the method can be duplicated on the same journal.
        - ``type``: Tuple containing one or both of these items: "bank" and "cash"
        - ``currency_ids``: The ids of the currency necessary on the journal (or company) for it to be eligible.
        - ``country_id``: The id of the country needed on the company for it to be eligible.
        """
        return {
            'manual': {'mode': 'multi', 'type': ('bank', 'cash', 'credit')},
        }

    @api.model
    def _get_sdd_payment_method_code(self):
        """
        TO OVERRIDE
        This hook will be used to return the list of sdd payment method codes
        """
        return []

    def unlink(self):
        self.env['account.payment.method.line'].search([('payment_method_id', 'in', self.ids)]).unlink()
        return super().unlink()


class AccountPaymentMethodLine(models.Model):
    _name = 'account.payment.method.line'
    _description = "Payment Methods"
    _order = 'sequence, id'

    # == Business fields ==
    name = fields.Char(compute='_compute_name', readonly=False, store=True)
    sequence = fields.Integer(default=10)
    payment_method_id = fields.Many2one(
        string='Payment Method',
        comodel_name='account.payment.method',
        domain="[('payment_type', '=?', payment_type), ('id', 'in', available_payment_method_ids)]",
        required=True,
    )
    payment_account_id = fields.Many2one(
        comodel_name='account.account',
        check_company=True,
        copy=False,
        ondelete='restrict',
        domain="['|', ('account_type', 'in', ('asset_current', 'liability_current')), ('id', '=', default_account_id)]"
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        check_company=True,
        index='btree_not_null',
    )
    default_account_id = fields.Many2one(
        related='journal_id.default_account_id'
    )

    # == Display purpose fields ==
    code = fields.Char(related='payment_method_id.code')
    payment_type = fields.Selection(related='payment_method_id.payment_type')
    company_id = fields.Many2one(related='journal_id.company_id')
    available_payment_method_ids = fields.Many2many(related='journal_id.available_payment_method_ids')

    @api.depends('journal_id')
    @api.depends_context('hide_payment_journal_id')
    def _compute_display_name(self):
        for method in self:
            if self.env.context.get('hide_payment_journal_id'):
                return super()._compute_display_name()
            method.display_name = f"{method.name} ({method.journal_id.name})"

    @api.depends('payment_method_id.name')
    def _compute_name(self):
        for method in self:
            if not method.name:
                method.name = method.payment_method_id.name

    @api.constrains('name')
    def _ensure_unique_name_for_journal(self):
        self.journal_id._check_payment_method_line_ids_multiplicity()

    def unlink(self):
        """
        Payment method lines which are used in a payment should not be deleted from the database,
        only the link betweend them and the journals must be broken.
        """
        unused_payment_method_lines = self
        for line in self:
            payment_count = self.env['account.payment'].sudo().search_count([('payment_method_line_id', '=', line.id)])
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
        if not account.reconcile and account.account_type not in ('asset_cash', 'liability_credit_card', 'off_balance'):
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
