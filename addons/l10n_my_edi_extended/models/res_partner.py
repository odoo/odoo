# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ------------------
    # Fields declaration
    # ------------------

    # Note: When merging with the base module in master, the company's industrial classification should become a related to this field.
    l10n_my_edi_industrial_classification = fields.Many2one(
        comodel_name='l10n_my_edi.industry_classification',
        string="Ind. Classification",
        compute='_compute_l10n_my_edi_industrial_classification',
        store=True,
        readonly=False,
    )
    l10n_my_edi_malaysian_tin = fields.Char(
        string="Malaysian TIN",
        help="The value set in this field will be used as TIN for the customer/supplier.\n"
             "If left empty, the Tax ID field will be used.",
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('l10n_my_edi_malaysian_tin')
    def _compute_l10n_my_tin_validation_state(self):
        # EXTEND 'l10n_my_edi' to add the depends
        super()._compute_l10n_my_tin_validation_state()

    def _compute_l10n_my_edi_industrial_classification(self):
        default_classification = self.env.ref('l10n_my_edi.class_00000', raise_if_not_found=False)
        self.filtered(lambda p: not p.l10n_my_edi_industrial_classification).l10n_my_edi_industrial_classification = default_classification

    # ----------------
    # Business methods
    # ----------------

    def _l10n_my_edi_get_tin_for_myinvois(self):
        # EXTEND 'l10n_my_edi'
        # When l10n_my_edi_malaysian_tin is set, it will be used instead of the VAT.
        # A user may want to keep the correct VAT on a foreign contact while also use myinvois with a malaysia TIN/Generic TIN
        # Using the Tax ID field also causes issue when base_vat is enabled, which block setting foreign VAT numbers.
        return self.l10n_my_edi_malaysian_tin or super()._l10n_my_edi_get_tin_for_myinvois()

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_my_edi_industrial_classification', 'l10n_my_edi_malaysian_tin']
