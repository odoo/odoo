# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

TAX_SYSTEM = [
    ("RF01", "[RF01] Ordinario"),
    ("RF02", "[RF02] Contribuenti minimi (art.1, c.96-117, L. 244/07)"),
    ("RF04", "[RF04] Agricoltura e attività connesse e pesca (artt.34 e 34-bis, DPR 633/72)"),
    ("RF05", "[RF05] Vendita sali e tabacchi (art.74, c.1, DPR. 633/72)"),
    ("RF06", "[RF06] Commercio fiammiferi (art.74, c.1, DPR  633/72)"),
    ("RF07", "[RF07] Editoria (art.74, c.1, DPR  633/72)"),
    ("RF08", "[RF08] Gestione servizi telefonia pubblica (art.74, c.1, DPR 633/72)"),
    ("RF09", "[RF09] Rivendita documenti di trasporto pubblico e di sosta (art.74, c.1, DPR  633/72)"),
    ("RF10", "[RF10] Intrattenimenti, giochi e altre attività di cui alla tariffa allegata al DPR 640/72 (art.74, c.6, DPR 633/72)"),
    ("RF11", "[RF11] Agenzie viaggi e turismo (art.74-ter, DPR 633/72)"),
    ("RF12", "[RF12] Agriturismo (art.5, c.2, L. 413/91)"),
    ("RF13", "[RF13] Vendite a domicilio (art.25-bis, c.6, DPR  600/73)"),
    ("RF14", "[RF14] Rivendita beni usati, oggetti d’arte, d’antiquariato o da collezione (art.36, DL 41/95)"),
    ("RF15", "[RF15] Agenzie di vendite all’asta di oggetti d’arte, antiquariato o da collezione (art.40-bis, DL 41/95)"),
    ("RF16", "[RF16] IVA per cassa P.A. (art.6, c.5, DPR 633/72)"),
    ("RF17", "[RF17] IVA per cassa (art. 32-bis, DL 83/2012)"),
    ("RF18", "[RF18] Altro"),
    ("RF19", "[RF19] Regime forfettario (art.1, c.54-89, L. 190/2014)"),
]


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_it_codice_fiscale = fields.Char(string="Codice Fiscale", size=16, related='partner_id.l10n_it_codice_fiscale',
        store=True, readonly=False, help="Fiscal code of your company")
    l10n_it_tax_system = fields.Selection(selection=TAX_SYSTEM, string="Tax System",
        help="Please select the Tax system to which you are subjected.")
    l10n_it_edi_proxy_user_id = fields.Many2one(
        comodel_name="account_edi_proxy_client.user",
        compute="_compute_l10n_it_edi_proxy_user_id",
    )
    l10n_it_edi_register = fields.Boolean(default=False)
    l10n_it_edi_purchase_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Italian Default Purchase Journal',
        domain=[('type', '=', 'purchase')],
        compute='_compute_l10n_it_edi_purchase_journal_id',
        store=True,
        readonly=False,
    )

    # Economic and Administrative Index
    l10n_it_has_eco_index = fields.Boolean(
        help="The seller/provider is a company listed on the register of companies and as\
        such must also indicate the registration data on all documents (art. 2250, Italian\
        Civil Code)")
    l10n_it_eco_index_office = fields.Many2one('res.country.state', domain="[('country_id','=','IT')]",
        string="Province of the register-of-companies office")
    l10n_it_eco_index_number = fields.Char(string="Number in register of companies", size=20,
        help="This field must contain the number under which the\
        seller/provider is listed on the register of companies.")
    l10n_it_eco_index_share_capital = fields.Float(string="Share capital actually paid up",
        help="Mandatory if the seller/provider is a company with share\
        capital (SpA, SApA, Srl), this field must contain the amount\
        of share capital actually paid up as resulting from the last\
        financial statement")
    l10n_it_eco_index_sole_shareholder = fields.Selection(
        [
            ("NO", "Not a limited liability company"),
            ("SU", "Socio unico"),
            ("SM", "Più soci")],
        string="Shareholder")
    l10n_it_eco_index_liquidation_state = fields.Selection(
        [
            ("LS", "The company is in a state of liquidation"),
            ("LN", "The company is not in a state of liquidation")],
        string="Liquidation state")


    # Tax representative
    l10n_it_has_tax_representative = fields.Boolean(
        help="The seller/provider is a non-resident subject which\
        carries out transactions in Italy with relevance for VAT\
        purposes and which takes avail of a tax representative in\
        Italy")
    l10n_it_tax_representative_partner_id = fields.Many2one('res.partner', string='Tax representative partner')

    @api.constrains('l10n_it_edi_purchase_journal_id')
    def _check_l10n_it_edi_purchase_journal_id(self):
        for company in self:
            if company.l10n_it_edi_purchase_journal_id and not company.l10n_it_edi_purchase_journal_id.default_account_id:
                raise ValidationError(_("The Italian default purchase journal requires a default account."))

    @api.constrains('l10n_it_has_eco_index',
                    'l10n_it_eco_index_office',
                    'l10n_it_eco_index_number',
                    'l10n_it_eco_index_liquidation_state')
    def _check_eco_admin_index(self):
        for record in self:
            if (record.l10n_it_has_eco_index
                and (not record.l10n_it_eco_index_office
                     or not record.l10n_it_eco_index_number
                     or not record.l10n_it_eco_index_liquidation_state)):
                raise ValidationError(_("All fields about the Economic and Administrative Index must be completed."))

    @api.constrains('l10n_it_has_eco_index',
                    'l10n_it_eco_index_share_capital',
                    'l10n_it_eco_index_sole_shareholder')
    def _check_eco_incorporated(self):
        """ If the business is incorporated, both these fields must be present.
            We don't know whether the business is incorporated, but in any case the fields
            must be both present or not present. """
        for record in self:
            if (record.l10n_it_has_eco_index
                and bool(record.l10n_it_eco_index_share_capital) ^ bool(record.l10n_it_eco_index_sole_shareholder)):
                raise ValidationError(_("If one of Share Capital or Sole Shareholder is present, "
                                        "then they must be both filled out."))

    @api.constrains('l10n_it_has_tax_representative',
                    'l10n_it_tax_representative_partner_id')
    def _check_tax_representative(self):
        for record in self:
            if not record.l10n_it_has_tax_representative:
                continue
            if not record.l10n_it_tax_representative_partner_id:
                raise ValidationError(_("You must select a tax representative."))
            if not record.l10n_it_tax_representative_partner_id.vat:
                raise ValidationError(_("Your tax representative partner must have a tax number."))
            if not record.l10n_it_tax_representative_partner_id.country_id:
                raise ValidationError(_("Your tax representative partner must have a country."))

    @api.depends("account_edi_proxy_client_ids", "l10n_it_codice_fiscale")
    def _compute_l10n_it_edi_proxy_user_id(self):
        for company in self:
            edi_company = company._l10n_it_get_edi_company()
            company.l10n_it_edi_proxy_user_id = edi_company.account_edi_proxy_client_ids.filtered(lambda x: x.proxy_type == 'l10n_it_edi')

            # If we can't find any proxy user, create a new demo proxy user for this italian company.
            # They must have the Codice Fiscale field filled for the registration process to work.
            if not company.l10n_it_edi_proxy_user_id and company.l10n_it_codice_fiscale:
                company.l10n_it_edi_proxy_user_id = self.env['account_edi_proxy_client.user']._register_proxy_user(
                    company=company,
                    proxy_type='l10n_it_edi',
                    edi_mode='demo',
                )

    @api.depends('country_code')
    def _compute_l10n_it_edi_purchase_journal_id(self):
        for company in self:
            if not company.l10n_it_edi_purchase_journal_id and company.country_code == 'IT':
                company.l10n_it_edi_purchase_journal_id = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company),
                    ('type', '=', 'purchase'),
                    ('default_account_id', '!=', False),
                ], limit=1)
            else:
                company.l10n_it_edi_purchase_journal_id = company.l10n_it_edi_purchase_journal_id

    def _l10n_it_edi_export_check(self):
        checks = {
            'company_vat_codice_fiscale_missing': {
                'fields': [('vat', 'l10n_it_codice_fiscale')],
                'message': _("Company/ies should have a VAT number or Codice Fiscale."),
            },
            'company_address_missing': {
                'fields': [('street', 'street2'), ('zip',), ('city',), ('country_id',)],
                'message': _("Company/ies should have a complete address, verify their Street, City, Zipcode and Country."),
            },
            'company_l10n_it_tax_system_missing': {
                'fields': [('l10n_it_tax_system',)],
                'message': _("Company/ies should have a Tax System"),
            },
        }
        errors = {}
        for key, check in checks.items():
            for fields_tuple in check.pop('fields'):
                if invalid_records := self.filtered(lambda record: not any(record[field] for field in fields_tuple)):
                    errors[f"l10n_it_edi_{key}"] = {
                        'message': check['message'],
                        'action_text': _("View Company/ies"),
                        'action': invalid_records._get_records_action(name=_("Check Company Data")),
                    }
        if self.filtered(lambda x: not x.l10n_it_edi_proxy_user_id):
            errors['l10n_it_edi_settings_l10n_it_edi_proxy_user_id'] = {
                'message': _("You need to set the Codice Fiscale on your company."),
                'action_text': _("View Company/ies"),
                'action': self._get_records_action(name=_("Check Company Data")),
            }
        return errors

    @api.onchange("l10n_it_has_tax_representative")
    def _onchange_l10n_it_has_tax_represeentative(self):
        for company in self:
            if not company.l10n_it_has_tax_representative:
                company.l10n_it_tax_representative_partner_id = False

    def _l10n_it_get_edi_company(self):
        self.ensure_one()
        if (
            self.root_id.id != self.id
            and self.l10n_it_codice_fiscale == self.root_id.l10n_it_codice_fiscale
            and self.vat == self.root_id.vat
        ):
            return self.root_id
        else:
            return self
