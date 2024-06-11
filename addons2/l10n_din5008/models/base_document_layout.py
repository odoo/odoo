from markupsafe import Markup
import re

from odoo import api, models, fields, _
from odoo.tools import format_date


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    @api.model
    def _default_report_footer(self):
        # OVERRIDE web/models/base_document_layout
        if self.env.company.external_report_layout_id == self.env.ref('l10n_din5008.external_layout_din5008'):
            company = self.env.company
            # Company VAT should not be present in this footer, as it is displayed elsewhere in the DIN5008 layout
            footer_fields = [field for field in [company.phone, company.email, company.website] if isinstance(field, str) and len(field) > 0]
            return Markup('<br>').join(footer_fields)
        return super()._default_report_footer()

    @api.model
    def _default_company_details(self):
        # OVERRIDE web/models/base_document_layout
        default_company_details = super()._default_company_details()
        if self.env.company.external_report_layout_id == self.env.ref('l10n_din5008.external_layout_din5008'):
            # In order to respect the strict formatting of DIN5008, we need to remove empty lines from the address
            return re.sub(r'(( )*<br>( )*\n)+', r'<br>\n', default_company_details)
        return default_company_details

    report_footer = fields.Html(default=_default_report_footer)
    company_details = fields.Html(default=_default_company_details)
    street = fields.Char(related='company_id.street', readonly=True)
    street2 = fields.Char(related='company_id.street2', readonly=True)
    zip = fields.Char(related='company_id.zip', readonly=True)
    city = fields.Char(related='company_id.city', readonly=True)
    company_registry = fields.Char(related='company_id.company_registry', readonly=True)
    bank_ids = fields.One2many(related='company_id.partner_id.bank_ids', readonly=True)
    account_fiscal_country_id = fields.Many2one(related='company_id.account_fiscal_country_id', readonly=True)
    l10n_din5008_template_data = fields.Binary(compute='_compute_l10n_din5008_template_data')
    l10n_din5008_document_title = fields.Char(compute='_compute_l10n_din5008_document_title')

    def _compute_l10n_din5008_template_data(self):
        self.l10n_din5008_template_data = [
            (_("Invoice No."), 'INV/2021/12345'),
            (_("Invoice Date"), format_date(self.env, fields.Date.today())),
            (_("Due Date"), format_date(self.env, fields.Date.add(fields.Date.today(), days=7))),
            (_("Delivery Date"), format_date(self.env, fields.Date.add(fields.Date.today(), days=7))),
            (_("Reference"), 'SO/2021/45678'),
        ]

    def _compute_l10n_din5008_document_title(self):
        self.l10n_din5008_document_title = _('Invoice')
