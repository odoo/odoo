from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_tr_gib_invoice_scenario = fields.Selection(
        selection=[
            ("TEMELFATURA", "Basic"),
            ("KAMU", "Public Sector"),
        ],
        default="TEMELFATURA",
        string="Invoice Scenario",
        help="Defines the official GİB (Turkish Revenue Administration) e-invoice "
        "scenario. \n"
        "Basic: Standard e-invoice that cannot be rejected by the recipient via the GİB portal. \n"
        "Public Sector: Used specifically for invoices issued to public (government) institutions.",
    )
    l10n_tr_gib_invoice_type = fields.Selection(
        compute="_compute_l10n_tr_gib_invoice_type",
        store=True,
        readonly=False,
        default="SATIS",
        string="GIB Invoice Type",
        selection=[
            ("SATIS", "Sales"),
            ("TEVKIFAT", "Withholding"),
            ("IHRACKAYITLI", "Registered for Export"),
            ("ISTISNA", "Tax Exempt"),
        ],
        help="Specifies the official GİB classification for the e-invoice/e-archive, which "
        "determines its tax treatment and validation rules. \n"
        "Sales: A standard sales invoice. \n"
        "Withholding: An invoice where the buyer is responsible for "
        "paying a portion of the VAT. \n"
        "Registered for Export: Invoice for goods that will later be exported."
        "If selected, an 'Exemption Reason' is required. \n"
        "Tax Exempt: An invoice for goods/services exempt from VAT. "
        "If selected, an 'Exemption Reason' is required.",
    )
    l10n_tr_is_export_invoice = fields.Boolean(
        string="Is GIB Export",
        help="Check this box if this is a product export invoice.",
    )
    l10n_tr_shipping_type = fields.Selection(
        selection=[
            ("1", "Sea Transportation"),
            ("2", "Railway Transportation"),
            ("3", "Road Transportation"),
            ("4", "Air Transportation"),
            ("5", "Post"),
            ("6", "Combined Transportation"),
            ("7", "Fixed Transportation"),
            ("8", "Domestic Water Transportation"),
            ("9", "Invalid Transportation Method"),
        ],
        string="Shipping Method",
        help="Specifies the method of transport using official GİB codes. ",
    )
    l10n_tr_exemption_code_id = fields.Many2one(
        "l10n_tr_nilvera_einvoice_extended.account.tax.code",
        compute="_compute_l10n_tr_exemption_code_id",
        store=True,
        readonly=False,
        string="Exemption Reason",
        help="The official GİB tax exemption reason. \n"
        "This field is mandatory if the 'GIB Invoice Type' is set to "
        "'Registered for Export' or 'Tax Exempt'",
    )
    l10n_tr_exemption_code_domain_list = fields.Binary(
        compute="_compute_l10n_tr_exemption_code_domain_list",
        help="Technical field (not for users). Used to dynamically filter the "
        "list of available exemption codes based on the selected "
        "GIB Invoice Type or other criteria.",
    )
    l10n_tr_nilvera_customer_status = fields.Selection(
        string="Partner Nilvera Status",
        related="partner_id.l10n_tr_nilvera_customer_status",
        help="Shows the Nilvera status of the customer. ",
    )


    @api.depends("l10n_tr_gib_invoice_scenario", "l10n_tr_gib_invoice_type", "l10n_tr_is_export_invoice")
    def _compute_l10n_tr_exemption_code_domain_list(self):
        for record in self:
            domain = []
            if record.l10n_tr_gib_invoice_type == "ISTISNA":
                domain.extend(("exception", "export_exception"))
            if record.l10n_tr_gib_invoice_type == "IHRACKAYITLI":
                domain.append("export_registration")
            if record.l10n_tr_is_export_invoice:
                domain.append("export_exception")
            record.l10n_tr_exemption_code_domain_list = domain

    @api.depends("l10n_tr_gib_invoice_scenario", "l10n_tr_is_export_invoice")
    def _compute_l10n_tr_gib_invoice_type(self):
        for record in self:
            record.l10n_tr_gib_invoice_type = False

    @api.depends("l10n_tr_gib_invoice_scenario", "l10n_tr_gib_invoice_type", "partner_id")
    def _compute_l10n_tr_exemption_code_id(self):
        for record in self:
            record.l10n_tr_exemption_code_id = False

    def _get_partner_l10n_tr_nilvera_customer_alias_name(self):
        self.ensure_one()
        if self.l10n_tr_is_export_invoice:
            return self.company_id.l10n_tr_nilvera_export_alias
        return super()._get_partner_l10n_tr_nilvera_customer_alias_name()
