from odoo import api, fields, models
from odoo.addons.l10n_cz_reports_2025.models.product_template import SUPPLIES_CODE_SELECTION, TRANSACTION_CODE_SELECTION, TRANSACTION_CODE_HELP
from odoo.tools.sql import column_exists, create_column


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_cz_transaction_code = fields.Selection(
        string="Transaction code",
        selection=TRANSACTION_CODE_SELECTION,
        compute='_compute_transaction_code',
        store=True,
        readonly=False,
        help=TRANSACTION_CODE_HELP,
    )

    # If a reverse charge transaction, user has to choose a reverse charge supply code.
    l10n_cz_supplies_code = fields.Selection(
        selection=SUPPLIES_CODE_SELECTION,
        string="Code of Supply",
        help="Code of subject of supply in the domestic reverse charge regime.",
        compute='_compute_l10n_cz_supplies_code',
        store=True,
        readonly=False,
    )

    # Helper field for defining when code of supply is mandatory
    is_reverse_charge = fields.Boolean(
        string="Is Reverse Charge",
        help="Whether line contains a tax related to reverse charge transactions",
        compute='_compute_is_reverse_charge',
    )

    def _auto_init(self):
        if not column_exists(self.env.cr, "account_move_line", "l10n_cz_transaction_code"):
            # Since l10n_cz_transaction_code column does not exist we can assume l10n_cz_supplies_code doesn't exist either
            create_column(self.env.cr, "account_move_line", "l10n_cz_transaction_code", "VARCHAR")
            create_column(self.env.cr, "account_move_line", "l10n_cz_supplies_code", "VARCHAR")
        return super()._auto_init()

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('product_id.l10n_cz_transaction_code')
    def _compute_transaction_code(self):
        for line in self:
            line.l10n_cz_transaction_code = line.product_id.l10n_cz_transaction_code

    @api.depends('tax_ids')
    def _compute_is_reverse_charge(self):
        for line in self:
            line.is_reverse_charge = any(line.tax_ids.mapped('l10n_cz_reverse_charge'))

    @api.depends('product_id.l10n_cz_supplies_code')
    def _compute_l10n_cz_supplies_code(self):
        for line in self:
            line.l10n_cz_supplies_code = line.product_id.l10n_cz_supplies_code
