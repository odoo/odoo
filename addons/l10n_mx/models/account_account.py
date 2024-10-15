import re
from odoo import _, api, Command, models
from odoo.exceptions import RedirectWarning
from odoo.tools import file_open
from odoo.tools.pycompat import csv_reader

with file_open('l10n_mx/data/account.group.template.csv', 'rb') as group_template_csv:
    reader = csv_reader(group_template_csv, delimiter=',', quotechar='"')
    SAT_GROUPS_CODES = {row[3] for row in reader}  # Getting every value from "code_prefix_start" column and removing quotes
ACCOUNT_ID_PATTERN = re.compile(r'\.\d{1,2}[1-9]')  # A dot, two or three digits, last digit cannot be 0


class AccountAccount(models.Model):
    _inherit = 'account.account'

    @api.model_create_multi
    def create(self, vals_list):
        # EXTENDS account - ensure there is a tag on created MX accounts
        # The computation is a bit naive and might not be correct in all cases.
        accounts = super().create(vals_list)
        debit_tag = self.env.ref('l10n_mx.tag_debit_balance_account')
        credit_tag = self.env.ref('l10n_mx.tag_credit_balance_account')
        mx_account_no_tags = accounts.filtered(lambda a: a.company_id.country_code == 'MX' and not a.tag_ids & (credit_tag + debit_tag))
        DEBIT_CODES = ['1', '5', '6', '7']  # all other codes are considered "credit"
        for account in mx_account_no_tags:
            tag_id = debit_tag.id if account.code[0] in DEBIT_CODES else credit_tag.id
            account.tag_ids = [Command.link(tag_id)]
        return accounts

    @api.constrains('code', 'group_id')
    def ensure_code_conforms_coa_sat(self):
        # filtering accounts used in Mexican reports that do not respect the regulation of the SAT (see documentation for more explanation)
        # six first characters correspond to the group provided, a list is provided by the SAT
        # last part is up to the user but should match ACCOUNT_ID_PATTERN which is detailed in the header
        incorrect_accounts = self.filtered(
            lambda a: a.group_id and a.account_type != 'equity_unaffected' and a.company_id.country_code == 'MX'
            and (a.code[:6] not in SAT_GROUPS_CODES or not ACCOUNT_ID_PATTERN.fullmatch(a.code[6:]))
        )
        if incorrect_accounts:
            account_names = '\n'.join(_('\t- %(name)s', name=account.name) for account in incorrect_accounts)
            raise RedirectWarning(
                _("Some of your accounts do not respect the SAT code regulation.\n\n%(account_names)s", account_names=account_names),
                {
                    'type': 'ir.actions.act_url',
                    'url': 'https://www.odoo.com/documentation/16.0/applications/finance/fiscal_localizations/mexico.html#chart-of-accounts'
                },
                _("Go to documentation")
            )
