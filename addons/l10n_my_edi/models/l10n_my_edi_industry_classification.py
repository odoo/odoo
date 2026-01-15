# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class L10nMyEdiIndustryClassification(models.Model):
    """
    These codes are required by the API. They represent the industry classifications that are used in Malaysia.
    As defined in the list of MSIC codes allowed here: https://sdk.myinvois.hasil.gov.my/codes/msic-codes/

    Made a model as the list of codes would be too long for a selection field, yet it is easier to provide users with
    the list than expect them to find and then enter both name and code manually.
    """
    _name = 'l10n_my_edi.industry_classification'
    _description = "Malaysian Industry Classification"

    # ------------------
    # Fields declaration
    # ------------------

    name = fields.Char(required=True)
    code = fields.Char(required=True)

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('code')
    def _compute_display_name(self):
        for classification in self:
            classification.display_name = f"{classification.code} {classification.name}"
