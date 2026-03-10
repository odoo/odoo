from odoo import api, fields, models


class L10nAccountWithholdingEntryLine(models.TransientModel):
    """
    Transient version of the withholding lines
    """
    _name = 'l10n.account.withholding.entry.line'
    _inherit = "account.withholding.line"
    _description = "Withholding Entry Line"

    withholding_entry_id = fields.Many2one(
        comodel_name='l10n.account.withholding.entry',
        string="Withholding Entry",
        required=True,
        ondelete='cascade',
    )
    withholding_account_ids = fields.One2many(
        comodel_name='account.account',
        compute='_compute_withholding_account_ids',
        string="Withhold Accounts",
    )
    withholding_tax_ids = fields.Many2many(
        comodel_name='account.tax',
        compute='_compute_withholding_tax_ids',
        string="Withhold Taxes",
    )
    tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="Withhold Tax",
        required=True,
        domain="[('company_id', '=', company_id), ('is_withholding_tax_on_payment', '=', True), ('id', 'in', withholding_tax_ids)]",
    )

    @api.depends('withholding_entry_id.company_id')
    def _compute_company_id(self):
        for line in self:
            line.company_id = line.withholding_entry_id.company_id

    @api.depends('withholding_entry_id.currency_id')
    def _compute_comodel_currency_id(self):
        for line in self:
            line.comodel_currency_id = line.withholding_entry_id.currency_id

    @api.depends('withholding_entry_id.date')
    def _compute_comodel_date(self):
        for line in self:
            line.comodel_date = line.withholding_entry_id.date

    @api.depends('withholding_entry_id.related_move_id.move_type')
    def _compute_type_tax_use(self):
        for line in self:
            if line.tax_id:
                line.type_tax_use = line.tax_id.type_tax_use
            else:
                line.type_tax_use = 'sale' if line.withholding_entry_id.related_move_id.is_sale_document() else 'purchase'

    def _compute_comodel_payment_type(self):
        for line in self:
            line.comodel_payment_type = 'inbound' if line.withholding_entry_id.related_move_id.is_sale_document() else 'outbound'

    def _get_comodel_partner(self):
        return self.withholding_entry_id.related_move_id.partner_id

    @api.depends('withholding_entry_id.related_move_id')
    def _compute_withholding_account_ids(self):
        for line in self:
            accounts = line.withholding_entry_id.related_move_id._get_withhold_account_by_sum().keys()
            line.withholding_account_ids = [acc._origin.id for acc in accounts]

    @api.depends('withholding_account_ids')
    def _compute_withholding_tax_ids(self):
        for line in self:
            line.withholding_tax_ids = line.withholding_account_ids.withholding_tax_section_id.tax_ids

    @api.depends('tax_id', 'withholding_entry_id.related_move_id')
    def _compute_base_amount(self):
        for line in self:
            if line.tax_id:
                withhold_account_by_sum = line.withholding_entry_id.related_move_id._get_withhold_account_by_sum()
                for account, amount in withhold_account_by_sum.items():
                    if line.tax_id in account.withholding_tax_section_id.tax_ids:
                        line.base_amount = amount
