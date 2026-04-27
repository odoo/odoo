# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_ke_validation_msg = fields.Json(
        string="Validation Message",
        compute='_compute_l10n_ke_validation_msg',
    )
    l10n_ke_error_msg = fields.Json(
        string="Error message from sending",
        copy=False,
    )
    l10n_ke_oscu_flow_type_code = fields.Selection(related='move_ids.l10n_ke_oscu_flow_type_code')
    l10n_ke_oscu_sar_number = fields.Integer(
        related='move_ids.l10n_ke_oscu_sar_number',
        readonly=True,
    )
    l10n_ke_state = fields.Selection(
        selection=[
            ('waiting_invoice', "Waiting for invoice"),
            ('to_send', "Not sent yet"),
            ('sent', "Sent")
        ],
        string="eTIMS Send Status",
        compute='_compute_l10n_ke_state',
    )

    @api.depends('move_ids.l10n_ke_oscu_sar_number',
                 'move_ids.l10n_ke_oscu_flow_type_code',
                 'state',
                 'partner_id')
    def _compute_l10n_ke_state(self):
        for pick in self:
            if (
                not pick.company_id.l10n_ke_oscu_is_active
                or not pick.l10n_ke_oscu_flow_type_code
                or pick.state != 'done'
                or all(not move.product_id.is_storable for move in pick.move_ids)
            ):
                pick.l10n_ke_state = False
                continue

            if all(move.l10n_ke_oscu_sar_number != 0 for move in pick.move_ids):
                pick.l10n_ke_state = 'sent'
                continue

            match pick.l10n_ke_oscu_flow_type_code:
                case '02' | '12':  # Incoming Purchase
                    purchase_lines = pick.move_ids.purchase_line_id
                    related_invoices = purchase_lines.invoice_lines.move_id
                    unfinished_purchases = any(
                        (
                            line.product_id.is_storable and
                            line.qty_received != line.qty_invoiced
                        ) for line in purchase_lines
                    )
                    if unfinished_purchases or not related_invoices or not all(related_invoices.mapped("l10n_ke_oscu_invoice_number")):
                        pick.l10n_ke_state = 'waiting_invoice'
                        continue
                    pick.l10n_ke_state = 'to_send'

                case '03' | '11':  # Outgoing Sale or Return Incoming
                    sale_lines = pick.move_ids.sale_line_id
                    related_invoices = sale_lines.invoice_lines.move_id
                    unmatched_sale_lines = any(
                        (
                            line.product_id.is_storable and
                            line.qty_delivered != line.qty_invoiced
                        ) for line in sale_lines
                    )
                    if unmatched_sale_lines or not related_invoices or not all(related_invoices.mapped("l10n_ke_oscu_invoice_number")):
                        pick.l10n_ke_state = 'waiting_invoice'
                        continue
                    pick.l10n_ke_state = 'to_send'

                case '01':  # Import Incoming
                    purchase_lines = pick.move_ids.purchase_line_id
                    if purchase_lines:
                        purchase = purchase_lines[0].order_id
                        quantities_details = purchase._l10n_ke_import_quantity_details(products=pick.move_ids.product_id)
                        if all(
                            product['received_quantity'] == product['import_expected_quantity']
                            for product in quantities_details.values()
                        ):
                            pick.l10n_ke_state = 'to_send'
                            continue
                    pick.l10n_ke_state = 'waiting_invoice'

                case _flowcode:
                    pick.l10n_ke_state = 'to_send'

    @api.depends('move_ids',
                 'move_ids.product_id',
                 'move_ids.product_uom',
                 'move_ids.l10n_ke_oscu_flow_type_code',
                 'l10n_ke_state')
    def _compute_l10n_ke_validation_msg(self):
        for pick in self:
            if (
                not pick.company_id.l10n_ke_oscu_is_active
                or not pick.move_ids
                or not pick.move_ids[0].l10n_ke_oscu_flow_type_code
            ):
                pick.l10n_ke_validation_msg = False
                continue

            pick_msg = {
                **pick.move_ids.product_id._l10n_ke_get_validation_messages(),
                **(pick.move_ids.product_uom | pick.move_ids.product_id.uom_id)._l10n_ke_get_validation_messages(),
            }
            if pick.l10n_ke_state == 'waiting_invoice':
                pick_msg['waiting_invoice'] = {
                    'message': _("The invoice/customs import must be confirmed first before sending this picking."),
                    'blocking': True,
                }
            if pick.l10n_ke_state == 'waiting_pos_order':
                pick_msg['waiting_pos_order'] = {
                    'message': _("The pos order must be confirmed first before sending this picking."),
                    'blocking': True,
                }
            pick.l10n_ke_validation_msg = pick_msg
