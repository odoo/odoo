from odoo import models, fields, _
from odoo.tools import format_date


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_din5008_addresses = fields.Binary(compute='_compute_l10n_din5008_addresses', exportable=False)

    def _compute_l10n_din5008_addresses(self):
        for record in self:
            record.l10n_din5008_addresses = data = []
            if not record.partner_id:
                continue
            if record.picking_type_id.code == 'incoming':
                data.append((_("Vendor Address:"), record.partner_id))
            elif record.picking_type_id.code == 'internal':
                data.append((_("Warehouse Address:"), record.partner_id))
            elif record.picking_type_id.code == 'outgoing':
                main_address_box = record.move_ids[0].partner_id if record.should_print_delivery_address() else record.partner_id
                if main_address_box.id != record.partner_id.commercial_partner_id.id:
                    data.append((
                        _("Beneficiary:"),
                        record.partner_id.commercial_partner_id,
                        # If the main delivery address is not the company address,
                        # the company address will have a separate beneficiary address block.
                        # The VAT number will not be displayed in the main address block,
                        # but in the beneficiary address block
                        {'show_tax_id': True},
                    ))
                if main_address_box.id != record.partner_id.id:
                    data.append((_("Customer Address:"), record.partner_id))

    def check_field_access_rights(self, operation, field_names):
        field_names = super().check_field_access_rights(operation, field_names)
        return [field_name for field_name in field_names if field_name not in {
            'l10n_din5008_addresses',
        }]
