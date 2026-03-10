# Copyright (C) 2012  Renato Lima - Akretion <renato.lima@akretion.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import _, fields, models

from ..constants.fiscal import TAX_DOMAIN_II, TAX_DOMAIN_IPI
from .ibpt import get_ibpt_product


class Ncm(models.Model):
    _name = "l10n_br_fiscal.ncm"
    _inherit = [
        "l10n_br_fiscal.data.ncm.nbs.abstract",
        "mail.thread",
        "mail.activity.mixin",
    ]
    _description = "NCM"

    code = fields.Char(size=10)

    code_unmasked = fields.Char(size=8)

    exception = fields.Char(size=2)

    tax_ipi_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Tax IPI",
        domain=[("tax_domain", "=", TAX_DOMAIN_IPI)],
    )

    tax_ii_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Tax II",
        domain=[("tax_domain", "=", TAX_DOMAIN_II)],
    )

    uot_id = fields.Many2one(comodel_name="uom.uom", string="Tax UoM")

    uoe_id = fields.Many2one(comodel_name="uom.uom", string="Export UoM")

    product_tmpl_ids = fields.One2many(inverse_name="ncm_id")

    tax_estimate_ids = fields.One2many(inverse_name="ncm_id")

    tax_definition_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.tax.definition",
        relation="tax_definition_ncm_rel",
        column1="ncm_id",
        column2="tax_definition_id",
        readonly=True,
        string="Tax Definition",
    )

    cest_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.cest",
        relation="fiscal_cest_ncm_rel",
        column1="ncm_id",
        column2="cest_id",
        readonly=True,
        string="CESTs",
    )

    nbm_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.nbm",
        relation="fiscal_nbm_ncm_rel",
        column1="ncm_id",
        column2="nbm_id",
        readonly=True,
        string="NBMs",
    )

    piscofins_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.tax.pis.cofins",
        relation="fiscal_pis_cofins_ncm_rel",
        column1="ncm_id",
        column2="piscofins_id",
        readonly=True,
        string="PIS/COFINS",
    )

    _sql_constraints = [
        (
            "fiscal_ncm_code_exception_uniq",
            "unique (code, exception)",
            _("NCM already exists with this code !"),
        )
    ]

    def _get_ibpt(self, config, code_unmasked):
        return get_ibpt_product(config, code_unmasked)
