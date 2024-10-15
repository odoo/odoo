from odoo import models, fields
from odoo.addons import account, stock


class ResCompany(stock.ResCompany, account.ResCompany):

    account_production_wip_account_id = fields.Many2one('account.account', string='Production WIP Account', check_company=True)
    account_production_wip_overhead_account_id = fields.Many2one('account.account', string='Production WIP Overhead Account', check_company=True)
