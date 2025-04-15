# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ---------------
    # Default methods
    # ---------------

    def _default_l10n_my_edi_industrial_classification(self):
        return self.env.ref('l10n_my_edi.class_00000', raise_if_not_found=False)

    # ------------------
    # Fields declaration
    # ------------------

    l10n_my_edi_proxy_user_id = fields.Many2one(
        comodel_name="account_edi_proxy_client.user",
        compute="_compute_l10n_my_edi_proxy_user_id",
    )
    l10n_my_identification_type = fields.Selection(related='partner_id.l10n_my_identification_type', readonly=False)
    l10n_my_identification_number = fields.Char(related='partner_id.l10n_my_identification_number', readonly=False)
    l10n_my_edi_industrial_classification = fields.Many2one(
        comodel_name='l10n_my_edi.industry_classification',
        string="Ind. Classification",
        default=_default_l10n_my_edi_industrial_classification,
    )
    l10n_my_edi_mode = fields.Selection(
        selection=[
            ('test', 'Pre-Production'),
            ('prod', 'Production'),
        ],
        # Nothing will happen until the user register, so it can be set by default.
        default="test",
    )
    # /!\ this was a planned feature that got scrapped due to API limitations. It may come back if their system provides better support for it.
    l10n_my_edi_default_import_journal_id = fields.Many2one(
        comodel_name="account.journal",
        domain="[('type', '=', 'purchase')]",
        string="Default import journal",
        help="The journal on which invoices imported from MyInvois will be booked. Leave empty to use the default purchase journal.",
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends("account_edi_proxy_client_ids", 'l10n_my_edi_mode')
    def _compute_l10n_my_edi_proxy_user_id(self):
        """ Each company is expected to have at most one proxy user for malaysia for each mode.
        Thus, we can easily find said user.
        """
        for company in self:
            company.l10n_my_edi_proxy_user_id = company.account_edi_proxy_client_ids.filtered(
                lambda u: u.proxy_type == 'l10n_my_edi' and u.edi_mode == company.l10n_my_edi_mode
            )[:1]

    # ----------------
    # Business methods
    # ----------------

    def _l10n_my_edi_create_proxy_user(self):
        """ This method will create a new proxy user for the current company based on the selected mode, if no users already exists. """
        self.ensure_one()
        if not self.l10n_my_edi_proxy_user_id:
            self.env['account_edi_proxy_client.user']._register_proxy_user(self, 'l10n_my_edi', self.l10n_my_edi_mode)
