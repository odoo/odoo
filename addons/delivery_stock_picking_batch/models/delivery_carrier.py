from odoo import models, _


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    def send_shipping(self, pickings):
        """ Send the package to the service provider

        :param pickings: A recordset of pickings
        :returns: A list of dictionaries (one per picking) containing of the form::
                {
                    'picking': {
                        'exact_price': price,
                        'tracking_number': number,
                        'delivery_labels': attachment_ids,
                        'return_labels': attachment_ids,
                        'shipping_docs': attachment_ids,
                        'error_messages': [string],
                    }
                }
        :rtype: dict[dict] | None
        """
        pickings_by_carrier = pickings.grouped('carrier_id')

        results = {}
        for carrier, picks in pickings_by_carrier.items():
            if hasattr(carrier, '%s_send_shipping' % carrier.delivery_type):
                if self._bundle_pickings(picks):
                    pick = picks[0]
                    pick_name = pick.name
                    pick.name = pick.batch_id.name
                    res = getattr(carrier, '%s_send_shipping' % carrier.delivery_type)(pick)
                    results[picks] = res[pick]
                    pick.name = pick_name
                else:
                    results |= getattr(carrier, '%s_send_shipping' % carrier.delivery_type)(picks)
            else:
                results |= {p: {
                    'exact_price': 0.0,
                    'delivery_labels': self.env['ir.attachment'],
                    'return_labels': self.env['ir.attachment'],
                    'delivery_docs': self.env['ir.attachment'],
                    'error_messages': [_("%s_send_shipping method not found!", carrier.delivery_type)],
                } for p in picks}
        return results

    def _bundle_pickings(self, pickings):
        bundle = True
        if not pickings:
            return False
        ref = pickings[0]
        # Check if each move line has a target package
        bundle &= len(ref.batch_id.move_line_ids.filtered(lambda move_line: move_line.result_package_id)) == len(ref.batch_id.move_line_ids)
        if not bundle:
            return False
        packages = set(ref.batch_id.move_line_ids.mapped(lambda move_line: move_line.result_package_id.name))
        bundle &= len(packages) == 1
        for picking in pickings[1:]:
            bundle &= ref.location_id == picking.location_id
            bundle &= ref.partner_id == picking.partner_id
        return bundle
