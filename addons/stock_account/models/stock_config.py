from odoo import fields, models

from odoo.addons.stock_account.models.constants import (
    COST_METHOD_SELECTION,
    VALUATION_SELECTION,
)


class StockConfig(models.Model):
    _inherit = "stock.config"

    account_stock_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Stock Journal",
        check_company=True,
    )
    account_stock_valuation_id = fields.Many2one(
        comodel_name="account.account",
        string="Stock Valuation Account",
        check_company=True,
    )
    account_production_wip_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Production WIP Account",
        check_company=True,
    )
    account_production_wip_overhead_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Production WIP Overhead Account",
        check_company=True,
    )
    inventory_period = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("daily", "Daily"),
            ("monthly", "Monthly"),
        ],
        default="manual",
        required=True,
    )
    inventory_valuation = fields.Selection(
        selection=VALUATION_SELECTION,
        string="Valuation",
        default="periodic",
    )
    cost_method = fields.Selection(
        selection=COST_METHOD_SELECTION,
        default="standard",
        required=True,
    )
