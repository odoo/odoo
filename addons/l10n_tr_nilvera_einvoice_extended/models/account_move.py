from odoo import api, fields, models
from odoo.tools.misc import unquote


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_tr_gib_invoice_scenario = fields.Selection(
        selection=[
            ("TEMELFATURA", "Basic"),
            ("KAMU", "Public Sector"),
        ],
        string="Invoice Scenario",
        help="The scenario of the invoice to be sent to GİB.",
    )

    l10n_tr_gib_invoice_type = fields.Selection(
        compute="_compute_l10n_tr_gib_invoice_type",
        store=True,
        readonly=False,
        selection=[
            ("SATIS", "Sales"),
            ("TEVKIFAT", "Withholding"),
            ("IHRACKAYITLI", "Registered for Export"),
            ("ISTISNA", "Tax Exempt"),
        ],
        string="Invoice Type",
        help="The type of sales invoice to be sent to GİB.",
    )

    l10n_tr_is_export_invoice = fields.Boolean(string="Is GIB Export")

    l10n_tr_shipping_type = fields.Selection(
        selection=[
            ("1", "Sea Transportation"),
            ("3", "Road Transport"),
            ("4", "Air Transportation"),
            ("5", "Post"),
        ],
        string="Shipping Method",
        help="The type of shipping.",
    )

    l10n_tr_exemption_code_id = fields.Many2one(
        "l10n_tr.account.tax.code",
        compute="_compute_l10n_tr_exemption_code_id",
        store=True,
        readonly=False,
        string="Exemption Reason",
        domain=lambda self: str(self._l10n_tr_exemption_code_domain()),
    )

    l10n_tr_exemption_code_domain_list = fields.Binary(
        compute="_compute_l10n_tr_exemption_code_domain_list"
    )

    l10n_tr_nilvera_customer_status = fields.Selection(
        string="Partner Nilvera Status",
        related="partner_id.l10n_tr_nilvera_customer_status",
    )

    def _l10n_tr_exemption_code_domain(self):
        return [
            ("code_type", "in", unquote("l10n_tr_exemption_code_domain_list") or []),
        ]

    @api.depends("l10n_tr_gib_invoice_scenario", "l10n_tr_gib_invoice_type")
    def _compute_l10n_tr_exemption_code_domain_list(self):
        for record in self:
            domain = []
            if record.l10n_tr_gib_invoice_type == "ISTISNA":
                domain.append("exception")
                domain.append("export_exception")
            if record.l10n_tr_gib_invoice_type == "IHRACKAYITLI":
                domain.append("export_registration")
            if record.l10n_tr_is_export_invoice:
                domain.append("export_exception")
            record.l10n_tr_exemption_code_domain_list = domain

    @api.depends("l10n_tr_gib_invoice_scenario", "l10n_tr_is_export_invoice")
    def _compute_l10n_tr_gib_invoice_type(self):
        self.l10n_tr_gib_invoice_type = False

    @api.depends("l10n_tr_gib_invoice_scenario", "l10n_tr_gib_invoice_type", "partner_id")
    def _compute_l10n_tr_exemption_code_id(self):
        self.l10n_tr_exemption_code_id = False

    def _get_partner_l10n_tr_nilvera_customer_alias_name(self):
        self.ensure_one()
        if self.l10n_tr_is_export_invoice:
            return "urn:mail:ihracatpk@gtb.gov.tr"
        return super()._get_partner_l10n_tr_nilvera_customer_alias_name()
