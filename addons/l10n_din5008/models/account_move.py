from odoo import models, fields, _
from odoo.tools import format_date


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_din5008_template_data = fields.Binary(compute='_compute_l10n_din5008_template_data')
    l10n_din5008_document_title = fields.Char(compute='_compute_l10n_din5008_document_title')
    l10n_din5008_addresses = fields.Binary(compute='_compute_l10n_din5008_addresses', exportable=False)

    def _compute_l10n_din5008_template_data(self):
        for record in self:
            record.l10n_din5008_template_data = data = []
            if record.name:
                data.append((_("Invoice No."), record.name))
            if record.invoice_date:
                data.append((_("Invoice Date"), format_date(self.env, record.invoice_date)))
            if record.invoice_date_due:
                data.append((_("Due Date"), format_date(self.env, record.invoice_date_due)))
            if record.delivery_date:
                data.append((_("Delivery Date"), format_date(self.env, record.delivery_date)))
            if record.invoice_origin:
                data.append((_("Source"), record.invoice_origin))
            if record.ref:
                data.append((_("Reference"), record.ref))

    def _compute_l10n_din5008_document_title(self):
        for record in self:
            record.l10n_din5008_document_title = ''
            if record.move_type == 'out_invoice':
                if record.state == 'posted':
                    record.l10n_din5008_document_title = _('Invoice')
                elif record.state == 'draft':
                    record.l10n_din5008_document_title = _('Draft Invoice')
                elif record.state == 'cancel':
                    record.l10n_din5008_document_title = _('Cancelled Invoice')
            elif record.move_type == 'out_refund':
                record.l10n_din5008_document_title = _('Credit Note')
            elif record.move_type == 'in_refund':
                record.l10n_din5008_document_title = _('Vendor Credit Note')
            elif record.move_type == 'in_invoice':
                record.l10n_din5008_document_title = _('Vendor Bill')

    def _compute_l10n_din5008_addresses(self):
        for record in self:
            record.l10n_din5008_addresses = data = []
            commercial_partner = record.partner_id.commercial_partner_id
            delivery_partner = record.partner_shipping_id
            invoice_partner = record.partner_id

            different_partner_count = len({partner.id for partner in [commercial_partner, delivery_partner, invoice_partner] if partner})
            # To avoid repetition in the address block.
            if different_partner_count <= 1:
                continue

            if delivery_partner and delivery_partner != commercial_partner:
                data.append((_("Shipping Address:"), delivery_partner))
            if invoice_partner and invoice_partner != commercial_partner:
                data.append((
                    _("Beneficiary:"),
                    commercial_partner,
                    # if the invoice address is different from the company address,
                    # the main address block will be the invoice address, and the
                    # vat number will only be shown in the beneficiary address block.
                    {'show_tax_id': True},
                ))

    def check_field_access_rights(self, operation, field_names):
        field_names = super().check_field_access_rights(operation, field_names)
        return [field_name for field_name in field_names if field_name not in {
            'l10n_din5008_addresses',
        }]
