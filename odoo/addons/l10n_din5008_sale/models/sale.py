from odoo import models, fields, _
from odoo.tools import format_date


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    l10n_din5008_template_data = fields.Binary(compute='_compute_l10n_din5008_template_data')
    l10n_din5008_document_title = fields.Char(compute='_compute_l10n_din5008_document_title')
    l10n_din5008_addresses = fields.Binary(compute='_compute_l10n_din5008_addresses', exportable=False)

    def _compute_l10n_din5008_template_data(self):
        for record in self:
            record.l10n_din5008_template_data = data = []
            if record.state in ('draft', 'sent'):
                if record.name:
                    data.append((_("Quotation No."), record.name))
                if record.date_order:
                    data.append((_("Quotation Date"), format_date(self.env, record.date_order)))
                if record.validity_date:
                    data.append((_("Expiration"), format_date(self.env, record.validity_date)))
            else:
                if record.name:
                    data.append((_("Order No."), record.name))
                if record.date_order:
                    data.append((_("Order Date"), format_date(self.env, record.date_order)))
            if record.client_order_ref:
                data.append((_('Customer Reference'), record.client_order_ref))
            if record.user_id:
                data.append((_("Salesperson"), record.user_id.name))
            if 'incoterm' in record._fields and record.incoterm:
                data.append((_("Incoterm"), record.incoterm.code))

    def _compute_l10n_din5008_document_title(self):
        for record in self:
            if self._context.get('proforma'):
                record.l10n_din5008_document_title = _('Pro Forma Invoice')
            elif record.state in ('draft', 'sent'):
                record.l10n_din5008_document_title = _('Quotation')
            else:
                record.l10n_din5008_document_title = _('Sales Order')

    def _compute_l10n_din5008_addresses(self):
        for record in self:
            record.l10n_din5008_addresses = data = []
            commercial_partner = record.partner_id.commercial_partner_id
            delivery_partner = record.partner_shipping_id
            invoice_partner = record.partner_invoice_id

            different_partner_count = len((commercial_partner | delivery_partner | invoice_partner).ids)
            # To avoid repetition in the address block.
            if different_partner_count <= 1:
                continue

            if self._context.get('proforma'):
                if delivery_partner and delivery_partner != commercial_partner:
                    data.append((_("Shipping Address:"), delivery_partner))
                if invoice_partner and invoice_partner != commercial_partner:
                    # if the proforma invoice has an invoice address different from the company address,
                    # the company address will have its separate address block.
                    # we will not display the VAT number in the main address block, but in the beneficiary block
                    data.append((_("Beneficiary:"), commercial_partner, {'show_tax_id': True}))
            else:
                if invoice_partner != delivery_partner and delivery_partner != commercial_partner:
                    data.append((_("Shipping Address:"), delivery_partner))
                if invoice_partner != delivery_partner and invoice_partner != commercial_partner:
                    data.append((_("Invoicing Address:"), invoice_partner))
                if invoice_partner == delivery_partner and invoice_partner != commercial_partner:
                    data.append((_("Invoicing and Shipping Address:"), invoice_partner))

    def check_field_access_rights(self, operation, field_names):
        field_names = super().check_field_access_rights(operation, field_names)
        return [field_name for field_name in field_names if field_name not in {
            'l10n_din5008_addresses',
        }]
