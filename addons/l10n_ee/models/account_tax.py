from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_ee_kmd_inf_code = fields.Selection(
        selection=[
            ("1", "Sale KMS §41/42"),
            ("2", "Sale KMS §41^1"),
            ("11", "Purchase KMS §29(4)/30/32"),
            ("12", "Purchase KMS §41^1"),
        ],
        string="KMD INF Code",
        default=False,
        help="This field is used for the comments/special code column in the KMD INF report.",
    )
