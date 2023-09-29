from odoo import models, fields, _
from odoo.tools import format_date


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_de_template_data = fields.Binary(compute='_compute_l10n_de_template_data')
    l10n_de_document_title = fields.Char(compute='_compute_l10n_de_document_title')
    l10n_de_addresses = fields.Binary(compute='_compute_l10n_de_addresses')

    def _compute_l10n_de_template_data(self):
        for record in self:
            record.l10n_de_template_data = data = []
            if record.name:
                data.append((_("Invoice No."), record.name))
            if record.invoice_date:
                data.append((_("Invoice Date"), format_date(self.env, record.invoice_date)))
            if record.invoice_date_due:
                data.append((_("Due Date"), format_date(self.env, record.invoice_date_due)))
            if record.invoice_origin:
                data.append((_("Source"), record.invoice_origin))
            if record.ref:
                data.append((_("Reference"), record.ref))

    def _compute_l10n_de_document_title(self):
        for record in self:
            record.l10n_de_document_title = ''
            if record.move_type == 'out_invoice':
                if record.state == 'posted':
                    record.l10n_de_document_title = _('Invoice')
                elif record.state == 'draft':
                    record.l10n_de_document_title = _('Draft Invoice')
                elif record.state == 'cancel':
                    record.l10n_de_document_title = _('Cancelled Invoice')
            elif record.move_type == 'out_refund':
                record.l10n_de_document_title = _('Credit Note')
            elif record.move_type == 'in_refund':
                record.l10n_de_document_title = _('Vendor Credit Note')
            elif record.move_type == 'in_invoice':
                record.l10n_de_document_title = _('Vendor Bill')

    def _compute_l10n_de_addresses(self):
        for record in self:
            record.l10n_de_addresses = data = []
            if 'partner_shipping_id' not in record._fields:
                data.append((_("Invoicing Address:"), record.partner_id))
            elif record.partner_shipping_id == record.partner_id:
                data.append((_("Invoicing and Shipping Address:"), record.partner_shipping_id))
            elif record.move_type in ("in_invoice", "in_refund") or not record.partner_shipping_id:
                data.append((_("Invoicing and Shipping Address:"), record.partner_id))
            else:
                data.append((_("Shipping Address:"), record.partner_shipping_id))
                data.append((_("Invoicing Address:"), record.partner_id))

    def check_field_access_rights(self, operation, field_names):
        field_names = super().check_field_access_rights(operation, field_names)
        return [field_name for field_name in field_names if field_name not in {
            'l10n_de_addresses',
        }]
