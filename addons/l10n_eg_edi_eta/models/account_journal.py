from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_eg_branch_id = fields.Many2one(
        comodel_name="res.partner",
        string="Branch",
        help="Address of the subdivision of the company.  You can just put the "
        "company partner if this is used for the main branch.",
        copy=False,
    )
    l10n_eg_activity_type_id = fields.Many2one(
        comodel_name="l10n_eg_edi.activity.type",
        string="ETA Activity Code",
        help="This is the activity type of the branch according to Egyptian Tax Authority",
        copy=False,
    )
    l10n_eg_branch_identifier = fields.Char(
        string="ETA Branch ID",
        help="This number can be found on the taxpayer profile on the eInvoicing portal. ",
        copy=False,
    )
