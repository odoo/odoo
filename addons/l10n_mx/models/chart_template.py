# coding: utf-8
# Copyright 2016 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    use_cash_basis = fields.Boolean(
        help='Select this if the tax should use cash basis, which will '
        'create an entry for this tax on a given account during '
        'reconciliation')
    cash_basis_account = fields.Many2one(
        'account.account.template', string='Tax Received Account',
        ondelete='restrict',
        help='Account use when creating entry for tax cash basis')

    def _get_tax_vals(self, company):
        """ This method add in dictionnary of all the values for the tax that
        will be created if will be assigned the cash basis account.
        """
        self.ensure_one()
        res = super(AccountTaxTemplate, self)._get_tax_vals(company)
        res.update({
            'use_cash_basis': self.use_cash_basis,
        })
        return res

    @api.multi
    def _generate_tax(self, company):
        """ This method update the return that generate taxes from templates.
            :param company: the company for which the taxes should be created
                from templates in self
            :returns: {
                'tax_template_to_tax': mapping between tax template and the
                    newly generated taxes corresponding,
                'account_dict': dictionary containing a to-do list with all
                    the accounts to assign on new taxes
            }
        """
        res = super(AccountTaxTemplate, self)._generate_tax(company)
        for tax in self:
            res.get('account_dict', {}).get(tax.id, {}).update({
                'cash_basis_account': tax.cash_basis_account.id})
        return res


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.multi
    def _load_template(
            self, company, code_digits=None, transfer_account_id=None,
            account_ref=None, taxes_ref=None):
        """ Generate all the objects from the templates
            :param company: company the wizard is running for
            :param code_digits: number of digits the accounts code should have
                in the COA
            :param transfer_account_id: reference to the account template
                that will be used as intermediary account for transfers between
                2 liquidity accounts
            :param acc_ref: Mapping between ids of account templates and real
                accounts created from them
            :param taxes_ref: Mapping between ids of tax templates and real
                taxes created from them
            :returns: tuple with a dictionary containing
                * the mapping between the account template ids and the ids of
                    the real accounts that have been generated
                    from them, as first item,
                * a similar dictionary for mapping the tax templates and taxes,
                    as second item,
            :rtype: tuple(dict, dict, dict)
            inherited to write the cash_basis_account in the created taxes
        """
        self.ensure_one()
        accounts, taxes = super(AccountChartTemplate, self)._load_template(
            company, code_digits=code_digits,
            transfer_account_id=transfer_account_id, account_ref=account_ref,
            taxes_ref=taxes_ref)
        if account_ref is None:
            account_ref = {}
        account_tax_obj = self.env['account.tax']

        for tax in self.tax_template_ids:
            account_tax_obj.browse(taxes.get(tax.id)).write({
                'cash_basis_account': account_ref.get(
                    tax.cash_basis_account.id, False),
            })
        return accounts, taxes
