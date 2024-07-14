# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import sample

from odoo import api, fields, models


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    iot_scale_ids = fields.Many2many(
        'iot.device',
        string="Scales",
        domain=[('type', '=', 'scale')],
        help="Choose the scales you want to use for this operation type. Those scales can be used to weigh the packages created."
    )
    auto_print_carrier_labels = fields.Boolean(
        "Auto Print Carrier Labels",
        help="If this checkbox is ticked, Odoo will automatically print the carrier labels of the picking when they are created. Note this requires a printer to be assigned to this report.")
    auto_print_export_documents = fields.Boolean(
        "Auto Print Export Documents",
        help="If this checkbox is ticked, Odoo will automatically print the export documents of the picking when they are created. Availability of export documents depends on the carrier and the destination. Note this requires a printer to be assigned to this report. ")


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        message = super(StockPicking, self).message_post(**kwargs)
        if message.attachment_ids:
            attachments_names = ''.join(message.attachment_ids.mapped('name'))
            report = self.env['ir.actions.report']
            # should only be 1 shipping attachment per message
            if self.picking_type_id.auto_print_carrier_labels and 'Label' in attachments_names:
                report = self.env['ir.actions.report']._get_report_from_name('delivery_iot.report_shipping_labels')
            elif self.picking_type_id.auto_print_export_documents and 'ShippingDoc' in attachments_names:
                report = self.env['ir.actions.report']._get_report_from_name('delivery_iot.report_shipping_docs')
            if report.device_ids:
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'iot_print_documents', {
                    'documents': message.attachment_ids.mapped('datas'),
                    'iot_device_identifier': report.device_ids[0].identifier,
                    'iot_ip': report.device_ids[0].iot_ip,
                    'iot_idempotent_ids': sample(range(1, 100000000), len(message.attachment_ids)),
                })
        return message
