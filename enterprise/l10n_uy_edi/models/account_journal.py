from odoo import api, models, fields


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_uy_edi_type = fields.Selection(
        selection=[
            ("electronic", "Electronic"),
            ("manual", "Manual"),
        ],
        string="Invoicing Type",
        compute="compute_l10n_uy_edi_type",
        precompute=True,
        store=True,
        copy=False,
        readonly=False,
        help="Type of journals that can be used for Uruguayan companies:\n"
        "* Electronic: To generate electronic documents via web service to DGI directly from Odoo\n"
        "* Manual: To add electronic documents that were created previously outside Odoo (example: backups,"
        " from Uruware, pre printed). This type is used to maintain the history and"
        " consistency of all the CFE (they will not create a new CFE in DGI)."
    )
    l10n_uy_edi_send_print = fields.Boolean(
        "Auto pop up Send and Print",
        help="Check this box to automatically open the Send and Print wizard after confirming your invoice. This will"
        " help ensure you don't forget to generate and send the required CFE (electronic tax document) to the"
        " government."
    )

    @api.depends("type")
    def compute_l10n_uy_edi_type(self):
        """
        Set default value if not value and journal type of type sale (If different journal type then clean up
        the value of the field
        """
        for journal in self:
            if journal.type == 'sale' and journal.country_code == 'UY' and not journal.l10n_uy_edi_type:
                journal.l10n_uy_edi_type = "electronic"
            else:
                journal.l10n_uy_edi_type = False
