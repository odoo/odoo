from odoo import fields, models, api
from odoo.tools import html2plaintext


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_fr_is_company_french = fields.Boolean(compute='_compute_l10n_fr_is_company_french')

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        company = self.env.company
        if view_type == 'form' and company.country_code in company._get_france_country_codes():
            shipping_fields = arch.xpath("//field[@name='partner_shipping_id']")
            if shipping_fields:
                shipping_fields[0].attrib.pop("groups", None)
        return arch, view

    @api.depends('company_id.country_code')
    def _compute_l10n_fr_is_company_french(self):
        for record in self:
            record.l10n_fr_is_company_french = record.country_code in record.company_id._get_france_country_codes()

    @api.depends("country_code", "move_type")
    def _compute_show_delivery_date(self):
        # EXTEND 'account'
        super()._compute_show_delivery_date()
        for move in self.filtered(lambda m: m.country_code == 'FR'):
            move.show_delivery_date = move.is_sale_document()

    def _l10n_fr_get_default_notes(self):
        self.ensure_one()
        # Mandatory / default notes for French e-invoicing [BR-FR-05]
        # Only add them for French companies
        if not self.company_id._invoice_is_french_company():
            return {}
        payment_term = self.invoice_payment_term_id
        return {
            'PMT': self.env._("In the event of late payment, a flat-rate fee of €40 for collection costs will be charged (Articles L.441-10 and D.441-5 of the Code de commerce)."),
            'PMD': self.env._("Late payment penalties at an annual rate of 10% are applied if the payment is made after the due date."),
            'AAB': html2plaintext(payment_term.note) if payment_term.early_discount else self.env._("No discount for early payment."),
        }
