# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# Copyright 2026 Auto-Info
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    bot_token = fields.Char(
        string="BOT Token",
        groups="base.group_system",
        help="Token used to call the Bank of Thailand exchange-rate API. "
        "The settings form renders it with widget=\"password\" so the value "
        "is masked on screen.",
    )
    autoinfo_currency_rate_last_update = fields.Datetime(
        string="Currency Rate Last Update",
        readonly=True,
    )
    autoinfo_currency_rate_last_rate_date = fields.Date(
        string="Currency Rate Last Rate Date",
        readonly=True,
    )
