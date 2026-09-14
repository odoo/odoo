import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"
    _CREDENTIAL_FIELDS = {
        "l10n_gr_edi_aade_key": "l10n_gr_edi_aade_key",
    }

    l10n_gr_edi_aade_id = fields.Char(string="AADE User ID")
    l10n_gr_edi_aade_key = fields.Char(
        string="AADE Subscription Key",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
    )
    l10n_gr_edi_branch_number = fields.Integer(
        related="partner_id.l10n_gr_edi_branch_number",
        readonly=False,
    )
    l10n_gr_edi_test_env = fields.Boolean(
        string="Greece Test Environment",
        default=True,
        help="Enable test environments with credentials obtained from https://mydata-dev-register.azurewebsites.net/",
    )
