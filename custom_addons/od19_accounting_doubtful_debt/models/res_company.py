from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    od19_doubtful_debt_expense_account_id = fields.Many2one(
        "account.account",
        string="Doubtful Debt Expense Account",
        domain="[('account_type', '=', 'expense')]",
        help="บัญชีค่าใช้จ่ายหนี้สงสัยจะสูญ (เดบิต)",
    )
    od19_doubtful_debt_allowance_account_id = fields.Many2one(
        "account.account",
        string="Doubtful Debt Allowance Account",
        domain="[('account_type', 'in', ('asset_current', 'asset_non_current'))]",
        help="บัญชีค่าเผื่อหนี้สงสัยจะสูญ (เครดิต) — บัญชีปรับมูลค่าลูกหนี้",
    )
    od19_doubtful_debt_journal_id = fields.Many2one(
        "account.journal",
        string="Doubtful Debt Journal",
        domain="[('type', '=', 'general')]",
        help="สมุดรายวันทั่วไปที่ใช้บันทึกค่าเผื่อและตัดหนี้สูญ",
    )
    od19_doubtful_debt_aging_line_ids = fields.One2many(
        "od19.doubtful.debt.aging.line",
        "company_id",
        string="Doubtful Debt Aging Buckets",
    )
