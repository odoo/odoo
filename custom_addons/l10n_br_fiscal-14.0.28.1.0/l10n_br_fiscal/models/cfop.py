# Copyright (C) 2013  Renato Lima - Akretion <renato.lima@akretion.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models

from ..constants.fiscal import (
    CFOP_DESTINATION,
    CFOP_DESTINATION_EXPORT,
    CFOP_DESTINATION_EXTERNAL,
    CFOP_DESTINATION_INTERNAL,
    CFOP_TYPE_MOVE,
    CFOP_TYPE_MOVE_DEFAULT,
    FISCAL_IN_OUT,
    FISCAL_OUT,
)


class Cfop(models.Model):
    _name = "l10n_br_fiscal.cfop"
    _inherit = "l10n_br_fiscal.data.abstract"
    _description = "CFOP"

    code = fields.Char(size=4)

    small_name = fields.Char(size=32, required=True)

    type_in_out = fields.Selection(
        selection=FISCAL_IN_OUT, string="Type", required=True, default=FISCAL_OUT
    )

    destination = fields.Selection(
        selection=CFOP_DESTINATION,
        help="Identifies the operation destination.",
        compute="_compute_destination",
        store=True,
    )

    is_import = fields.Boolean(
        string="Is Import?",
        compute="_compute_is_import",
    )

    cfop_inverse_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.cfop",
        string="Inverse CFOP",
        domain="[('destination', '=', destination),"
        "('type_in_out', '!=', type_in_out)]",
    )

    cfop_return_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.cfop",
        string="Return CFOP",
        domain="[('destination', '=', destination),"
        "('type_in_out', '!=', type_in_out),"
        "('type_move', 'in', ('sale_refund',"
        " 'purchase_refund', 'return_out', 'return_in'))]",
    )

    stock_move = fields.Boolean(string="Stock Moves?", default=True)

    finance_move = fields.Boolean(string="Finance Moves?", default=True)

    account_move = fields.Boolean(string="Account Move?", default=True)

    assent_move = fields.Boolean(string="Assent Move?", default=False)

    type_move = fields.Selection(
        selection=CFOP_TYPE_MOVE,
        required=True,
        default=CFOP_TYPE_MOVE_DEFAULT,
    )

    ind_nfe = fields.Selection(
        selection=[
            ("0", "0 - No"),
            ("1", "1 - Yes"),
        ],
        string="Used in NFe",
        required=True,
        default="0",
    )

    ind_cte = fields.Selection(
        selection=[
            ("0", "0 - No"),
            ("1", "1 - Yes"),
        ],
        string="Used in CTe",
        required=True,
        default="0",
    )

    ind_comunica = fields.Selection(
        selection=[
            ("0", "0 - No"),
            ("1", "1 - Yes"),
        ],
        string="Communication?",
        required=True,
        default="0",
    )

    ind_transp = fields.Selection(
        selection=[
            ("0", "0 - No"),
            ("1", "1 - Yes"),
        ],
        string="Transport?",
        required=True,
        default="0",
    )

    ind_devol = fields.Selection(
        selection=[
            ("0", "0 - No"),
            ("1", "1 - Yes"),
        ],
        string="Return?",
        required=True,
        default="0",
    )

    ind_retor = fields.Selection(
        selection=[
            ("0", "0 - No"),
            ("1", "1 - Yes"),
        ],
        string="Regress?",
        required=True,
        default="0",
    )

    ind_anula = fields.Selection(
        selection=[
            ("0", "0 - No"),
            ("1", "1 - Yes"),
        ],
        string="Revocation?",
        required=True,
        default="0",
    )

    ind_remes = fields.Selection(
        selection=[
            ("0", "0 - No"),
            ("1", "1 - Yes"),
        ],
        string="Shipment?",
        required=True,
        default="0",
    )

    ind_comb = fields.Selection(
        selection=[
            ("0", "0 - No"),
            ("1", "1 - Yes - Without mandatory transportation information"),
            ("2", "2 - Yes - With mandatory transportation information"),
        ],
        string="Fuel?",
        required=True,
        default="0",
    )

    tax_definition_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.tax.definition",
        inverse_name="cfop_id",
        string="Tax Definition",
    )

    def _compute_is_import(self):
        for cfop in self:
            if cfop.code:
                cfop.is_import = cfop.code[0:1] == "3"
            else:
                cfop.is_import = False

    @api.depends("code")
    def _compute_destination(self):
        """Compute the destination based on the first digit of the CFOP code"""
        for cfop in self:
            if cfop.code:
                first_digit = cfop.code[0:1]
                if first_digit in ["1", "5"]:
                    cfop.destination = CFOP_DESTINATION_INTERNAL
                elif first_digit in ["2", "6"]:
                    cfop.destination = CFOP_DESTINATION_EXTERNAL
                elif first_digit in ["3", "7"]:
                    cfop.destination = CFOP_DESTINATION_EXPORT
                else:
                    cfop.destination = False
            else:
                cfop.destination = False

    _sql_constraints = [
        (
            "fiscal_cfop_code_uniq",
            "unique (code)",
            "CFOP already exists with this code !",
        )
    ]
