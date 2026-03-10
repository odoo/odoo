# Copyright (C) 2019  Renato Lima - Akretion <renato.lima@akretion.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import _, fields, models

from ..constants.fiscal import TAX_DOMAIN


class TaxGroup(models.Model):
    _name = "l10n_br_fiscal.tax.group"
    _description = "Tax Group"
    _order = "sequence, name, tax_domain"

    name = fields.Char(required=True)

    sequence = fields.Integer(
        default=10,
        required=True,
        help="The sequence field is used to define the "
        "order in which taxes are displayed.",
    )

    compute_sequence = fields.Integer(
        default=10,
        required=True,
        help="The sequence field is used to define "
        "order in which the tax lines are applied.",
    )

    tax_scope = fields.Selection(
        selection=[
            ("city", _("City")),
            ("state", _("State")),
            ("federal", _("Federal")),
            ("other", _("Other")),
        ],
        required=True,
    )

    tax_domain = fields.Selection(selection=TAX_DOMAIN, required=True)

    tax_include = fields.Boolean(string="Tax Included in Price", default=False)

    tax_withholding = fields.Boolean(default=False)

    # PIS / COFINS
    base_without_icms = fields.Boolean(
        string="Remove ICMS value from Base",
        default=False,
    )

    base_with_additional_values = fields.Boolean(
        string="Add the value of freight, insurance and others to the Base",
        default=True,
    )

    tax_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.tax", inverse_name="tax_group_id", string="Taxes"
    )

    cst_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.cst", inverse_name="tax_group_id", string="CSTs"
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="WH Partner",
    )

    wh_due_day = fields.Integer(
        string="Due Day",
    )

    _sql_constraints = [
        (
            "fiscal_tax_group_code_uniq",
            "unique (name)",
            _("Tax Group already exists with this name !"),
        )
    ]
