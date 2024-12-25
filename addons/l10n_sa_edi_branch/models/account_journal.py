from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_sa_branch_crn = fields.Char("Branch CRN",
        copy=False,
        help="Can be used when the company has multiple branches that share the same VAT number, but have different commercial registration numbers.\
        Keep this field empty to use the Identification Number set on the company.",
        compute="_compute_l10n_sa_branch_crn",
        store=True,
        readonly=False,
        tracking=True,)
    l10n_sa_use_branch_crn = fields.Boolean(related="company_id.l10n_sa_use_branch_crn")

    @api.depends("company_id.l10n_sa_use_branch_crn")
    def _compute_l10n_sa_branch_crn(self):
        # Reset l10n_sa_branch_crn to False when Branch CRN setting is deactivated
        self.filtered(lambda journal: not journal.company_id.l10n_sa_use_branch_crn).l10n_sa_branch_crn = False
