# Part of Odoo. See LICENSE file for full copyright and licensing details.
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.fields import Domain


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    def _get_default_weight_uom(self):
        return self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    batch_group_by_carrier = fields.Boolean('Carrier', help="Automatically group batches by carriers")
    batch_max_weight = fields.Integer("Maximum weight",
                                      help="A transfer will not be automatically added to batches that will exceed this weight if the transfer is added to it.\n"
                                           "Leave this value as '0' if no weight limit.")
    weight_uom_name = fields.Char(string='Weight unit of measure label', compute='_compute_weight_uom_name', readonly=True, default=_get_default_weight_uom)

    def _compute_weight_uom_name(self):
        for picking_type in self:
            picking_type.weight_uom_name = self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    @api.model
    def _get_batch_group_by_keys(self):
        return super()._get_batch_group_by_keys() + ['batch_group_by_carrier']


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def send_to_shipper(self):
        if len(self) == 1:
            return super().send_to_shipper()

        for batch, pickings in self.grouped("batch_id").items():
            results = pickings.carrier_id.send_shipping(pickings)

            expanded_results = {}
            for pickings, shipment in results.items():
                for picking in pickings:
                    expanded_results[picking] = shipment
                    picking.carrier_price = picking.carrier_id._apply_margins(shipment.get('exact_price', 0.0), picking.sale_id)
                self._post_shipment_in_batch(pickings, shipment)

            super()._update_tracking_number(expanded_results)
            super()._post_shipping_information(expanded_results)

    def _post_shipment_in_batch(self, pickings, shipment):
        if not pickings or not pickings[0].batch_id:
            return
        picking = pickings[0]
        target = picking.batch_id
        order_currency = picking.sale_id.currency_id or picking.company_id.currency_id
        carrier_name = picking.carrier_id.name

        if len(shipment.get("delivery_docs", [])):
            doc_msg = Markup('<b>%(header)s</b>') % {'header': _("Shipping Documents Attached")}
            target.message_post(body=doc_msg, attachment_ids=shipment["delivery_docs"].ids)

        if len(shipment.get("return_labels", [])):
            ret_msg = Markup('<b>%(header)s</b>') % {'header': _("Return Labels Generated")}
            target.message_post(body=ret_msg, attachment_ids=shipment["return_labels"].ids)

        if len(shipment.get("delivery_labels", [])):
            del_msg = Markup("<b>%(header)s</b>") % {'header': _("Delivery Labels Generated")}
            target.message_post(body=del_msg, attachment_ids=shipment["delivery_labels"].ids)

        main_msg = Markup("""
            <h6 class="mb-0 fw-bold">%(header)s</h6>
            <ul class="mb-2">
                <li><b>%(tracking_label)s:</b> %(tracking_ref)s</li>
                <li><b>%(cost_label)s:</b> %(price).2f %(currency)s</li>
            </ul>
        """) % {
            'header': _("%(batch_ref)s Processed by %(carrier_name)s", batch_ref=','.join(pickings.mapped('name')), carrier_name=carrier_name),
            'tracking_label': _("Tracking Number"),
            'tracking_ref': shipment.get('tracking_number', _('N/A')),
            'cost_label': _("Cost"),
            'price': picking.carrier_price,
            'currency': order_currency.name,
        }
        target.message_post(body=main_msg)

        if shipment.get("error_messages"):
            li_elements = [Markup("<li>%s</li>") % error for error in shipment.get('error_messages')]
            errors_html = Markup('<ul class="mb-2">%s</ul>') % Markup("").join(li_elements)
            error_msg = Markup("""
                <div class="alert alert-warning border-warning border-1 p-3" role="alert">
                    <h6 class="alert-heading mb-0 fw-bold">%(header)s</h6>
                    <div class="mb-2">
                        %(error_text)s
                    </div>
                </div>
            """) % {
                'header': _("Notice from %(carrier_name)s", carrier_name=carrier_name),
                'error_text': errors_html,
            }
            target.message_post(body=error_msg)

    def _get_possible_pickings_domain(self):
        domain = super()._get_possible_pickings_domain()
        if self.picking_type_id.batch_group_by_carrier:
            domain &= Domain('carrier_id', '=', self.carrier_id.id if self.carrier_id else False)

        return domain

    def _get_possible_batches_domain(self):
        domain = super()._get_possible_batches_domain()
        if self.picking_type_id.batch_group_by_carrier:
            domain &= Domain('picking_ids.carrier_id', '=', self.carrier_id.id if self.carrier_id else False)

        return domain

    def _get_auto_batch_description(self):
        description = super()._get_auto_batch_description()
        if self.picking_type_id.batch_group_by_carrier and self.carrier_id:
            description = f"{description}, {self.carrier_id.name}" if description else self.carrier_id.name
        return description

    def _is_auto_batchable(self, picking=None):
        """ Verifies if a picking can be put in a batch with another picking without violating auto_batch constrains.
        """
        res = super()._is_auto_batchable(picking)
        if not picking:
            picking = self.env['stock.picking']
        if self.picking_type_id.batch_max_weight:
            res = res and (self.weight + picking.weight <= self.picking_type_id.batch_max_weight)
        return res
