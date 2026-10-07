from odoo import api, fields, models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner']

    invoice_edi_format = fields.Selection(selection_add=[('ubl_tr', "Türkiye (UBL TR 1.2)")])
    l10n_tr_edi_customer_status = fields.Selection(
        selection=[
            ('not_checked', "Not Verified"),
            ('earchive', "E-Archive"),
            ('einvoice', "E-Invoice"),
        ],
        string="E-Document Status",
        copy=False,
        default='not_checked',
        readonly=True,
        tracking=True,
        help="By clicking 'Verify', Odoo will check if this partner is compliant with e-Invoice or e-Archive system.",
    )

    # This field is only used technically for optimisation purposes. It's needed for _check_nilvera_customer.
    l10n_tr_edi_alias_ids = fields.One2many(
        comodel_name='l10n_tr_edi.alias',
        inverse_name="partner_id",
        help="Specifies the alias provided by Nilvera, used when sending electronic invoices. \n"
        "It helps make sure your customer is correctly recognized by the GİB when e-invoices are sent. \n"
        "This ID is needed for your invoices to be processed correctly and comply with Turkish tax rules.",
    )

    @api.depends('invoice_edi_format')
    def _compute_is_company(self):
        # Any partner that has the ubl_tr invoicing format set will be categorized as follows
        # A company has a 10-digit or less Tax ID (VKN) & an individual contact has an 11-digit or more Tax ID (TCKN)
        l10n_tr_partners = self.env['res.partner']
        for partner in self:
            if partner.invoice_edi_format != "ubl_tr":
                continue
            partner.is_company = False
            if partner.has_vat and partner.vat.isdigit() and len(partner.vat) <= 10:
                partner.is_company = True
            l10n_tr_partners += partner

        super(ResPartner, self - l10n_tr_partners)._compute_is_company()

    def _get_suggested_invoice_edi_format(self):
        # EXTENDS 'account'
        res = super()._get_suggested_invoice_edi_format()
        if self.country_code == 'TR':
            return 'ubl_tr'
        else:
            return res

    def _get_edi_builder(self, invoice_edi_format):
        # EXTENDS 'account_edi_ubl_cii'
        if invoice_edi_format == 'ubl_tr':
            return self.env['account.edi.xml.ubl.tr']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats_info(self):
        # EXTENDS 'account_edi_ubl_cii'
        formats_info = super()._get_ubl_cii_formats_info()
        formats_info['ubl_tr'] = {'countries': ['TR']}
        return formats_info
