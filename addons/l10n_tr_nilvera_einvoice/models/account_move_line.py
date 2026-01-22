from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_tr_ctsp_number = fields.Char(
        string="CTSP Number",
        compute="_compute_l10n_tr_ctsp_number",
        store=True,
        readonly=False,
    )
    l10n_tr_seller_line_code = fields.Char(
        string="Seller Line Code",
        compute='_compute_l10n_tr_seller_line_code',
        store=True,
        readonly=False,
    )
    l10n_tr_customer_line_code = fields.Char(
        string="Customer Line Code",
        help="Customer Line Code (11 or fewer characters)",
        size=11,
        compute='_compute_l10n_tr_customer_line_code',
        store=True,
        readonly=False,
    )

    l10n_tr_original_line_id = fields.Many2one("account.move.line", readonly=True)

    l10n_tr_original_quantity = fields.Float(
        string="Original Quantity",
        digits="Product Unit",
        help="The quantity originally sold for this product.",
    )

    l10n_tr_original_tax_without_withholding = fields.Monetary(
        string="Original Tax After Withholding",
        help="Taxes collected after deducting withholding taxes for this product on the original invoice.",
    )

    @api.depends("product_id.l10n_tr_ctsp_number")
    def _compute_l10n_tr_ctsp_number(self):
        for record in self:
            record.l10n_tr_ctsp_number = record.product_id.l10n_tr_ctsp_number

    @api.constrains("l10n_tr_ctsp_number")
    def _check_l10n_tr_ctsp_number(self):
        for record in self:
            if record.l10n_tr_ctsp_number and len(record.l10n_tr_ctsp_number) > 12:
                raise ValidationError(_("CTSP Number must be 12 digits or fewer."))

    @api.depends("product_id.l10n_tr_seller_line_code")
    def _compute_l10n_tr_seller_line_code(self):
        for record in self:
            record.l10n_tr_seller_line_code = record.product_id.l10n_tr_seller_line_code

    @api.depends("product_id.l10n_tr_customer_line_code")
    def _compute_l10n_tr_customer_line_code(self):
        for record in self:
            record.l10n_tr_customer_line_code = record.product_id.l10n_tr_customer_line_code
