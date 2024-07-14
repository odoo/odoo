# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class SaftAccount(models.Model):

    _name = 'l10n_at_saft.account'
    _description = "Information for the SAF-T export about a virtual account from the chart of accounts given in the Austrian SAF-T specification; each (accounting) account has to be mapped to such a virtual account for the SAF-T export"
    _order = 'code'
    _rec_names_search = ['name', 'code']

    name = fields.Char(
        string="Name",
        help="Called \"Bezeichnung\" in the Austrian SAF-T documentation",
        required=True)
    code = fields.Char(
        string="Code",
        help="Called \"Konto Nr\" in the Austrian SAF-T documentation",
        size=64,
        required=True)
    account_type = fields.Char(
        string="Account Type",
        help="Called \"Kontenart (Ka)\" in the Austrian SAF-T documentation",
        size=1,
        required=True)
    account_class = fields.Char(
        string="Account Class",
        help="Called \"Kontenklasse (Kl)\" in the Austrian SAF-T documentation",
        size=1,
        required=True)

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for account in self:
            account.display_name = f"{account.code} {account.name}"
