import logging
import pprint

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.sale_gelato_connector.utils import make_gelato_request, split_partner_name

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()
        for sale_order in self:
            if (
                sale_order.company_id.gelato_api_key
                and sale_order.order_line.filtered(lambda g: g.product_id.gelato_reference)
            ):
                sale_order.send_gelato_order_request()

        return res

    def send_gelato_order_request(self):

        shipping = self.order_line.filtered(
            lambda l: l.is_delivery and l.product_id.default_code in ['normal', 'express']
        )

        url = 'https://order.gelatoapis.com/v4/orders'
        payload = {
            'orderType': "order",
            'orderReferenceId': self.id,
            'customerReferenceId': self.partner_id.id,
            'currency': self.currency_id.name,
            'items': self.get_gelato_items(),
            'shipmentMethodUid': shipping.product_id.default_code or 'cheapest',
            'shippingAddress': self.get_gelato_shipping_address(),
        }

        response = make_gelato_request(self.company_id, url=url, data=payload)

        if response.ok:
            self.message_post(
                body=_("Order %s has been passed to Gelato successfully", self.display_name),
                author_id=self.env.ref('base.partner_root').id,
            )

        else:
            error_message = response.json().get('message')
            self.message_post(
                body=_("Order %s has not been passed to Gelato. Following information were given: "
                       "%s", self.display_name, error_message),
                author_id=self.env.ref('base.partner_root').id,
            )

        _logger.info('Notification received from Gelato with data:\n%s',
                     pprint.pformat(response.json()))

    def get_gelato_shipping_address(self):

        first_name, last_name = split_partner_name(self.partner_shipping_id.name)
        return {
            'companyName': self.partner_shipping_id.commercial_company_name or '',
            'firstName': first_name or last_name,  # Gelato doesn't accept empty string
            'lastName': last_name,
            'addressLine1': self.partner_shipping_id.street,
            'addressLine2': self.partner_shipping_id.street2 or '',
            'state': self.partner_shipping_id.state_id.code,
            'city': self.partner_shipping_id.city,
            'postCode': self.partner_shipping_id.zip,
            'country': self.partner_shipping_id.country_id.code,
            'email': self.partner_shipping_id.email,
            'phone': self.partner_shipping_id.phone or ''
        }

    def get_gelato_items(self):

        gelato_items = []
        gelato_lines = self.order_line.filtered(lambda s: s.product_id.gelato_reference)
        for sale_order_line in gelato_lines:
            base_url = self.get_base_url()
            image_url = base_url + self.image_url(
                record=sale_order_line.product_id.product_tmpl_id,
                field='gelato_template_image'
            )
            gelato_item = {
                'itemReferenceId': sale_order_line.product_id.id,
                'productUid': str(sale_order_line.product_id.gelato_reference),
                'files': [
                    {
                        'type': 'default',
                        'url': image_url
                    }
                ],
                'quantity': int(sale_order_line.product_uom_qty)
            }
            gelato_items.append(gelato_item)

        return gelato_items

    @staticmethod
    def image_url(record, field):
        """ Returns a local url that points to the image field of a given browse record. """

        domain = [
            ('res_model', '=', record._name),
            ('res_field', '=', field),
            ('res_id', 'in', [record.id]),
        ]
        # Note: the 'bin_size' flag is handled by the field 'datas' itself
        attachment = record.env['ir.attachment'].sudo().search(domain)
        access_token = attachment.generate_access_token()

        return str(attachment.image_src) + '?access_token=' + access_token[0]

    def write(self, values):
        res = super().write(values)
        ngp = []
        gp = []
        for line in self.order_line.filtered(lambda l: l.product_id.product_tmpl_id.sale_ok):
            if line.product_id.gelato_reference:
                gp.append(line.product_id.name)
            else:
                ngp.append(line.product_id.name)
        if ngp and gp:
            raise UserError(_(
                "Products %s and %s can't be in the same order", ",".join(gp), ",".join(ngp)
            ))
        return res

    def create(self, vals_list):
        res = super().create(vals_list)

        gp = []
        ngp = []
        for line in res.order_line.filtered(lambda l: l.product_id.product_tmpl_id.sale_ok):
            if line.product_id.gelato_reference:
                gp.append(line.product_id.name)
            else:
                ngp.append(line.product_id.name)
        if ngp and gp:
            raise UserError(_(
                "Products %s and %s can't be in the same order.", ",".join(gp), ",".join(ngp)
            ))
        return res

    def action_open_delivery_wizard(self):
        view_id = self.env.ref('delivery.choose_delivery_carrier_view_form').id

        # if product in sale order is gelato one then propose the gelato delivery
        if (any(line.product_id.gelato_reference for line in self.order_line)
            and not self.env.context.get('carrier_recompute')):
            name = _('Add a shipping method')
            carrier = (
                self.env['delivery.carrier'].search([('delivery_type', '=', 'gelato')], limit=1)
            )

            return {
                'name': name,
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'choose.delivery.carrier',
                'view_id': view_id,
                'views': [(view_id, 'form')],
                'target': 'new',
                'context': {
                    'default_order_id': self.id,
                    'default_carrier_id': carrier.id,
                    'default_total_weight': self._get_estimated_weight()
                }
            }

        return super().action_open_delivery_wizard()
