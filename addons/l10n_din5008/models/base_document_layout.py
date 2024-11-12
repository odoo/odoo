from markupsafe import Markup
import re
from dateutil.relativedelta import relativedelta

from odoo import api, models, fields


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
    l10n_din5008_invoice_date = fields.Date(default=fields.Date.today, store=False)
    l10n_din5008_due_date = fields.Date(default=fields.Date.today() + relativedelta(day=7), store=False)
    l10n_din5008_delivery_date = fields.Date(default=fields.Date.today() + relativedelta(day=7), store=False)
