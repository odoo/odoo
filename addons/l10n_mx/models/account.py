# coding: utf-8
# Copyright 2016 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import re
from odoo import models, api, fields, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def _prepare_liquidity_account(self, name, company, currency_id, type):
        '''
        This function prepares the value to use for the creation of the default debit and credit accounts of a
        liquidity journal (created through the wizard of generating COA from templates for example).

        :param name: name of the bank account
        :param company: company for which the wizard is running
        :param currency_id: ID of the currency in which is the bank account
        :param type: either 'cash' or 'bank'
        :return: mapping of field names and values
        :rtype: dict
        '''
        res = super(AccountJournal, self)._prepare_liquidity_account(name, company, currency_id, type)
        code = res.get('code')
        account = self.env['account.account']
        if account.search_tags(code) and company.country_id.id == self.env.ref('base.mx').id:
            res.update({
                'tag_ids': [(6, 0, [tag.id for tag in account.search_tags(code)])]
            })
        return res

class AccountAccount(models.Model):
    _inherit = 'account.account'

    @api.multi
    def assign_account_tag(self):
        """Based on account code will be assigned by default the corresponding tag by tag code, this method is designed
        to be called from a server action in order to ensure in the background the tag is being assigned.

        The server action should be created like this:

        ```
        for record in records:
            if record.company_id.country_id.id == env.ref('base.mx').id:
                record.assign_account_tag()
        ```
        """
        for account in self:
            tag = account.search_tags(account.code)
            tags = tag | account.tag_ids.filtered(lambda r: r.color not in [4])
            if tags:
                account.write({'tag_ids': [(6, 0, [t.id for t in tags])]})

    @api.model
    def search_tags(self, code):
        account_tag = self.env['account.account.tag']
        if not self.search_regex(code):
            return account_tag
        account = self.get_account_tuple(code)
        tag = account_tag.search([
            ('name', 'like', "%s.%s%%" % (account[0], account[1])),
            ('color', '=', 4)], limit=1)
        return tag

    @api.onchange('code')
    def _onchange_code(self):
        if self.company_id.country_id.id == self.env.ref('base.mx').id and self.code:
            tags = self.search_tags(self.code)
            self.tag_ids = tags

    @api.model
    def search_regex(self, code):
        """Given a code return the code divided in three groups of elements
        separated wither by dash and/or dot in order to be used in the tag
        assignations and/or report generation.

        :param code: Text like 102.11.222
        :return: Regex search result
        """
        return re.search(
            '^(?P<first>[1-8][0-9][0-9])[,.]'
            '(?P<second>[0-9][0-9])[,.]'
            '(?P<third>[0-9]{2,3})$', code)

    @api.model
    def get_account_tuple(self, code):
        """Given a code get the elements of that code divided
        consistently with the separation declared in search_regex
        method.

        :param code: Text like 102.11.222
        :return: A tuple with the first and the second part of the code
        """
        return self.search_regex(code).groups()


class AccountAccountTag(models.Model):
    _inherit = 'account.account.tag'

    nature = fields.Selection([
        ('D', _('Debitable Account')), ('A', _('Creditable Account'))],
        help='Used in Mexican report of electronic accounting (account nature).')
