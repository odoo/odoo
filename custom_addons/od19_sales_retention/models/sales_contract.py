from odoo import api, fields, models


class Od19SalesContract(models.Model):
    _inherit = "od19.sales.contract"

    od19_retention_account_id = fields.Many2one(
        "account.account",
        string="Retention Receivable Account",
        domain="[('account_type', '=', 'asset_receivable')]",
        help="ลูกหนี้เงินประกันผลงาน - the account the withheld retention is "
        "parked in. Must differ from the customer trade receivable so the "
        "output VAT (ภ.พ.30) is not affected.",
    )
    od19_retention_journal_id = fields.Many2one(
        "account.journal",
        string="Retention Journal",
        domain="[('type', '=', 'general')]",
        help="Journal used to post retention hold and release entries.",
    )
    od19_default_retention_rate = fields.Float(
        string="Default Retention Rate (%)",
        digits=(5, 2),
        help="Default withholding percentage applied to new installments.",
    )
    od19_default_retention_days = fields.Integer(
        string="Retention Release (days)",
        help="Number of days after the invoice date when the retention is due "
        "to be released. Used to derive the release date.",
    )
    od19_retention_ids = fields.One2many(
        "od19.sales.retention",
        "contract_id",
        string="Retentions",
    )
    od19_retention_held_amount = fields.Float(
        compute="_compute_od19_retention_totals",
        store=True,
        help="Total retention currently held for this contract.",
    )
    od19_retention_released_amount = fields.Float(
        compute="_compute_od19_retention_totals",
        store=True,
        help="Total retention already released for this contract.",
    )

    @api.depends("od19_retention_ids.retention_amount", "od19_retention_ids.state")
    def _compute_od19_retention_totals(self):
        for contract in self:
            held = contract.od19_retention_ids.filtered(
                lambda retention: retention.state == "held"
            )
            released = contract.od19_retention_ids.filtered(
                lambda retention: retention.state in ("released", "closed")
            )
            contract.od19_retention_held_amount = sum(
                held.mapped("retention_amount")
            )
            contract.od19_retention_released_amount = sum(
                released.mapped("retention_amount")
            )
