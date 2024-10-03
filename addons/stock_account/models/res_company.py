from odoo import models, fields

from odoo.addons.stock_account import const


class ResCompany(models.Model):
    _name = "res.company"
    _inherit = "res.company"

    account_production_wip_account_id = fields.Many2one('account.account', string='Production WIP Account', check_company=True)
    account_production_wip_overhead_account_id = fields.Many2one('account.account', string='Production WIP Overhead Account', check_company=True)
    cost_method = fields.Selection(
        string="Cost Method",
        selection=const.COST_METHOD,
        default="standard",
        required=True,
    )
