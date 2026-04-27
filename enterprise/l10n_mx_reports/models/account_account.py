import re
import csv

from odoo import api, fields, models
from odoo.tools import file_open

with file_open('l10n_mx/data/template/account.group-mx.csv') as group_template_csv:
    reader = csv.reader(group_template_csv, delimiter=',', quotechar='"')
    SAT_GROUPS_CODES = {row[2] for row in reader}
ACCOUNT_ID_PATTERN = re.compile(r'\d{3}\.\d{2}\.\d*')


class AccountAccount(models.Model):
    _inherit = 'account.account'

    l10n_mx_is_sat_invalid = fields.Boolean(compute="_compute_l10n_mx_is_sat_invalid")

    @api.depends('code')
    def _compute_l10n_mx_is_sat_invalid(self):
        # filtering accounts used in Mexican reports that do not respect the regulation of the SAT (see documentation for more explanation)
        # six first characters correspond to the group provided, a list is provided by the SAT
        # last part is up to the user but should match ACCOUNT_ID_PATTERN which is detailed in the header
        current_company = self.env.company
        incorrect_accounts = self.filtered(
            lambda a: current_company.country_code == "MX" and
                a.code and current_company in a.company_ids
                and (a.code.rpartition('.')[0] not in SAT_GROUPS_CODES or not ACCOUNT_ID_PATTERN.fullmatch(a.code))
        )
        (self - incorrect_accounts).l10n_mx_is_sat_invalid = False
        incorrect_accounts.l10n_mx_is_sat_invalid = True
