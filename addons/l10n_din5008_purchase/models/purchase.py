from odoo import models, fields, _
from odoo.tools import format_date


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    l10n_din5008_template_data = fields.Binary(compute='_compute_l10n_din5008_template_data')
    l10n_din5008_document_title = fields.Char(compute='_compute_l10n_din5008_document_title')
    l10n_din5008_addresses = fields.Binary(compute='_compute_l10n_din5008_addresses', exportable=False)

    def _compute_l10n_din5008_template_data(self):
        for record in self:
            record.l10n_din5008_template_data = data = []
            if record.state == 'draft':
                data.append((_("Request for Quotation No."), record.name))
            elif record.state in ['sent', 'to approve', 'purchase', 'done']:
                data.append((_("Purchase Order No."), record.name))
            elif record.state == 'cancel':
                data.append((_("Cancelled Purchase Order No."), record.name))

            if record.user_id:
                data.append((_("Purchase Representative"), record.user_id.name))
            if record.partner_ref:
                data.append((_("Order Reference"), record.partner_ref))
            if record.date_approve:
                data.append((_("Order Date"), format_date(self.env, record.date_approve)))
            elif record.date_order:
                data.append((_("Order Deadline"), format_date(self.env, record.date_order)))
            if record.incoterm_id:
                data.append((_("Incoterm"), record.incoterm_id.code))



    def _compute_l10n_din5008_document_title(self):
        for record in self:
            if record.state in ['draft', 'sent', 'to approve']:
                record.l10n_din5008_document_title = _("Request for Quotation")
            elif record.state in ['purchase', 'done']:
                record.l10n_din5008_document_title = _("Purchase Order")
            elif record.state == 'cancel':
                record.l10n_din5008_document_title = _("Cancelled Purchase Order")

    def _compute_l10n_din5008_addresses(self):
        for record in self:
            record.l10n_din5008_addresses = data = []
            if record.dest_address_id:
                data.append((_("Shipping Address:"), record.dest_address_id))
            elif 'picking_type_id' in record._fields and record.picking_type_id.warehouse_id:
                data.append((_("Shipping Address:"), record.picking_type_id.warehouse_id.partner_id))

    def check_field_access_rights(self, operation, field_names):
        field_names = super().check_field_access_rights(operation, field_names)
        return [field_name for field_name in field_names if field_name not in {
            'l10n_din5008_addresses',
        }]
