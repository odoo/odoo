from odoo import fields, models


class AccountGroup(models.Model):
    _inherit = "account.group"

    full_name_on_account = fields.Boolean(
        help="If set the name on the account will be shown using the full path in the group.")

    def name_get(self):
        # if not self.full_name_on_account:
        #     return super().name_get()
        result = []
        for group in self:
            if not group.parent_id:
                continue
            me = group
            name = group.name
            if group.code_prefix and not group.parent_id:
                code = '[' + group.code_prefix + '] '
                name = code + name
            result.append((group.id, name))
            while group.parent_id:
                group = group.parent_id
                name = group.name + " / " + name
            result.append((me.id, "[%s] %s" % (me.code_prefix, name)))
        return result


class AccountAccount(models.Model):
    _inherit = "account.account"

    def name_get(self):
        if not self.env.company.country_id == self.env.ref('base.pe'):
            return super().name_get()
        """For Peru the tree view is important because the last name of the account is a construction of the tree on 
        groups by law (using the groups as a reporter for the tree view only)."""
        result = []
        for account in self:
            name = ''
            if not account.group_id:
                name = '[' + account.code + '] ' + account.name
            if account.group_id.name == account.name:
                if not isinstance(account.group_id.display_name, bool):
                    name = account.group_id.display_name.replace(  # TODO:
                        account.group_id.code_prefix, account.code)
            if not name:
                if not isinstance(account.group_id.display_name, bool):
                    element = account.group_id.display_name.replace(
                        account.group_id.code_prefix, account.code)
                    name = element + ': ' + account.name
            result.append((account.id, name))
        return result

class AccountJournal(models.Model):
    _inherit = "account.journal"

    def create(self, vals):
        journal = super().create(vals)
        if not journal.company_id.country_id == self.env.ref('base.pe') or not journal.default_debit_account_id:
            return journal
        """For Peru it will not make sense an auto created account without group then simply adding this helper for
        more information we did it for the core but it was refused, if you decide make this in the core here is the PR
        related for a quick reference and avoid empty debates. https://github.com/odoo/odoo/pull/33079 this would be
        more elegant if we had a _prepare_account_vals method for this creation (I could not solve the liquidity
        transfer account with this technique because it is auto install:  True and I can not inherit from here its
        behavior without have a recursive problem)."""
        journal.default_debit_account_id.onchange_code()
        return journal
