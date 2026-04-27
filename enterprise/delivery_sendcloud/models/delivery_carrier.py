# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tools import float_is_zero, float_round

from .sendcloud_service import SendCloud


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(selection_add=[
        ('sendcloud', 'Sendcloud')
    ], ondelete={'sendcloud': lambda records: records.write({'delivery_type': 'fixed', 'fixed_price': 0})})

    country_id = fields.Many2one('res.country', string='Ship From', compute='_compute_country_id', store=True, readonly=False)
    sendcloud_public_key = fields.Char(help="Sendcloud API Integration Public key", groups="base.group_system")
    sendcloud_secret_key = fields.Char(help="Sendcloud API Integration Secret key", groups="base.group_system")
    sendcloud_default_package_type_id = fields.Many2one("stock.package.type", string="Default Package Type for Sendcloud", help="Some carriers require package dimensions, you can define these in a package type that you set as default")
    sendcloud_shipping_id = fields.Many2one('sendcloud.shipping.product', store=True, compute='_compute_sendcloud_shipping_id', copy=False)
    sendcloud_return_id = fields.Many2one('sendcloud.shipping.product', store=True, compute='_compute_sendcloud_return_id', copy=False)
    sendcloud_shipping_name = fields.Char(related='sendcloud_shipping_id.name', string="Sendcloud Shipping Product")
    sendcloud_return_name = fields.Char(related='sendcloud_return_id.name', string="Sendcloud Return Shipping Product")
    sendcloud_shipping_rules = fields.Boolean(string="Use Sendcloud shipping rules",
                                              help="Depending your Sendcloud account type, through rules you can define the shipping method to use depending on different conditions like destination, weight, value, etc.\nRules can override shipping product selected in Odoo")
    sendcloud_product_functionalities = fields.Json(string="Functionalities")
    sendcloud_has_custom_functionalities = fields.Boolean(
        related="sendcloud_shipping_id.can_customize_functionalities")
    sendcloud_can_batch_shipping = fields.Boolean(
        related="sendcloud_shipping_id.has_multicollo")
    sendcloud_use_batch_shipping = fields.Boolean(
        string="Use Batch Shipping",
        help="When sending multiple parcels, combine them in one shipment. Not supported for international shipping requiring customs' documentation",)

    @api.constrains('delivery_type', 'sendcloud_public_key', 'sendcloud_secret_key')
    def _check_sendcloud_api_keys(self):
        for rec in self:
            if rec.delivery_type == 'sendcloud' and not (rec.sudo().sendcloud_public_key and rec.sudo().sendcloud_secret_key):
                raise ValidationError(_('You must add your public and secret key for sendcloud delivery type!'))

    @api.depends('delivery_type')
    def _compute_can_generate_return(self):
        super()._compute_can_generate_return()
        self.filtered(lambda c: c.delivery_type == 'sendcloud').can_generate_return = True

    @api.depends('country_id')
    def _compute_sendcloud_shipping_id(self):
        self.sendcloud_shipping_id = False

    @api.depends('country_id')
    def _compute_sendcloud_return_id(self):
        self.sendcloud_return_id = False

    def write(self, vals):
        original_sendcloud_product_ids = set(self.sendcloud_shipping_id.ids + self.sendcloud_return_id.ids)
        res = super().write(vals)
        to_delete_sendcloud_product_ids = original_sendcloud_product_ids - set(self.sendcloud_shipping_id.ids + self.sendcloud_return_id.ids)
        if to_delete_sendcloud_product_ids:
            self.env['sendcloud.shipping.product'].browse(to_delete_sendcloud_product_ids).unlink()
        return res

    def action_load_sendcloud_shipping_products(self):
        """
        Returns a wizard to choose from available sendcloud shipping products.
        Since the shipping product ids in sendcloud change overtime they are not saved,
        instead they are fetched everytime and passed to the context of the wizard
        """
        self.ensure_one()
        if self.delivery_type != 'sendcloud':
            raise ValidationError(_('Must be a Sendcloud carrier!'))
        if not self.country_id:
            raise UserError(_("You must assign the required 'Shipping From' field in order to search for available products"))
        sendcloud = self._get_sendcloud()
        # Get normal and return shipping products (can't get both at once)
        shipping_products = sendcloud._get_shipping_products(from_country=self.country_id.code)
        return_products = sendcloud._get_shipping_products(from_country=self.country_id.code, is_return=True)
        if not shipping_products:
            raise UserError(_("There are no shipping products available, please update the 'Shipping From' field or activate suitable carriers in your sendcloud account"))

        return {
            'name': _("Choose Sendcloud Shipping Products"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sendcloud.shipping.wizard',
            'target': 'new',
            'context': {
                'default_carrier_id': self.id,
                'default_shipping_products': shipping_products,
                'default_return_products': return_products,
                'default_sendcloud_products_code': {
                    'shipping': self.sendcloud_shipping_id.sendcloud_code or shipping_products[0].get('code', False),
                    'return': self.sendcloud_return_id.sendcloud_code or False,
                },
            },
        }

    def rate_shipment(self, order):
        res = super().rate_shipment(order)
        if hasattr(self, '%s_rate_shipment' % self.delivery_type):
            if res.get('no_rate'):
                res['warning_message'] = _('There is no rate available for this order with the selected shipping product.')
        return res

    def sendcloud_rate_shipment(self, order):
        """ Returns shipping rate for the order and chosen shipping method """
        order_weight = self.env.context.get('order_weight', None)
        sendcloud = self._get_sendcloud()
        try:
            result = sendcloud._get_shipping_rate(self, order=order, order_weight=order_weight)
            if not result:
                return {
                    'success': True,
                    'price': 0.0,
                    'no_rate': True,
                }
            price, packages_no = result
        except (UserError, ValidationError) as e:
            return {
                'success': False,
                'price': 0.0,
                'error_message': str(e),
            }
        messages = []
        if packages_no > 1:
            messages.append(_("Note that this price is for %s packages since the order weight is more than the maximum weight allowed by the shipping method.", packages_no))

        # Check if the products individually fit in the delivery method
        max_weight_user_uom = self.sendcloud_convert_weight(self.sendcloud_shipping_id.max_weight - 1, grams=True, reverse=True)
        for sol in order.order_line:
            # We only assume the following as a warning as there's no notion of unbreakable unit in Odoo
            if sol.product_id.weight > max_weight_user_uom:
                messages.append(_("Note that a unit of the product '%s' is heavier than the maximum weight allowed by the shipping method.", sol.product_id.name))
                break
        message = "\n".join(messages) if messages else None
        return {
            'success': True,
            'price': price,
            'warning_message': message
        }

    def sendcloud_send_shipping(self, pickings):
        ''' Sends Shipment to sendcloud, must request rate to return exact price '''
        sendcloud = self._get_sendcloud()
        res = []
        for pick in pickings:
            # multiple parcels if several packages used
            parcels = sendcloud._send_shipment(pick)
            # fetch the ids, tracking numbers and url for each parcel
            parcel_ids, parcel_tracking_numbers, doc_ids = self._prepare_track_message_docs(pick, parcels, sendcloud)
            pick.message_post_with_source(
                'delivery_sendcloud.sendcloud_label_tracking',
                render_values={'type': 'Shipment', 'parcels': parcels},
                subtype_xmlid='mail.mt_note',
                attachment_ids=doc_ids.ids,
            )
            pick.sendcloud_parcel_ref = parcel_ids
            try:
                # generate return if config is set
                if pick.carrier_id.return_label_on_delivery:
                    self.get_return_label(pick)
            except UserError:
                # if the return fails need to log that they failed and continue
                pick.message_post(body=_('Failed to create the return label!'))

            try:
                # get exact price of shipment
                price = 0.0
                for parcel in parcels:
                    # get price for each parcel
                    shipping_rate = sendcloud._get_shipping_rate(pick.carrier_id, picking=pick, parcel=parcel)
                    if shipping_rate:
                        price += shipping_rate[0]
            except UserError:
                # if the price fetch fails need to log that they failed and continue
                pick.message_post(body=_('Failed to get the actual price!'))

            # get tracking numbers for parcels
            parcel_tracking_numbers = ','.join(parcel_tracking_numbers)
            # if in test env, sendcloud does not have one, so we cancel the shipment ASAP
            if not self.prod_environment:
                self.cancel_shipment(pick)
                msg = _("Shipment %s cancelled", parcel_tracking_numbers)
                pick.message_post(body=msg)
                parcel_tracking_numbers = None
            res.append({
                'exact_price': price,
                'tracking_number': parcel_tracking_numbers
            })
        return res

    def sendcloud_get_tracking_link(self, picking):
        sendcloud = self._get_sendcloud()
        if not picking.sendcloud_parcel_ref:
            return
        # since there can be more than one id stored, comma seperated, only the first will be tracked
        parcel_id = picking.sendcloud_parcel_ref[0]
        if isinstance(parcel_id, list):  # Multicollo
            parcel_id = parcel_id[0]
        res = sendcloud._track_shipment(parcel_id)
        return res['tracking_url']

    def sendcloud_get_return_label(self, picking, tracking_number=None, origin_date=None):
        sendcloud = self._get_sendcloud()
        parcels = sendcloud._send_shipment(picking=picking, is_return=True)
        # fetch the ids, tracking numbers and url for each parcel
        parcel_ids, _, doc_ids = self._prepare_track_message_docs(picking, parcels, sendcloud)
        # Add Tracking info and docs in chatter
        picking.message_post_with_source(
            'delivery_sendcloud.sendcloud_label_tracking',
            render_values={'type': 'Return', 'parcels': parcels},
            subtype_xmlid='mail.mt_note',
            attachment_ids=doc_ids.ids
        )
        # if picking is not a return means we are pregenerating the return label on delivery
        # thus we save the returned parcel id in a seperate field
        if picking.is_return_picking:
            picking.sendcloud_parcel_ref = parcel_ids
        else:
            picking.sendcloud_return_parcel_ref = parcel_ids

    def sendcloud_cancel_shipment(self, pickings):
        sendcloud = self._get_sendcloud()
        failed_call = []
        for pick in pickings:
            parcels = (pick.sendcloud_parcel_ref or []) + (pick.sendcloud_return_parcel_ref or [])
            for parcel_id in parcels:
                if isinstance(parcel_id, list):
                    # In Multicollo, cancelling 1 parcel of the bactch cancel the whole batch
                    parcel_id = parcel_id[0]
                res = sendcloud._cancel_shipment(parcel_id)
                if res.get('status') not in ['deleted', 'cancelled', 'queued']:
                    failed_call.append(parcel_id)
        if failed_call:
            details = ",".join(str(p_id) for p_id in failed_call)
            raise UserError(f"The cancellation was rejected for the parcel(s) with the following id :\n{details}\nEither :\n\t - The parcel is already cancelled\n\t - The parcel has been announced more than 42 days ago\n\t - The parcel has already been delivered")

    def sendcloud_convert_weight(self, weight, grams=False, reverse=False):
        """
            Each API request for sendcloud usually requires
            weight in kilograms but pricing supports grams.
        """
        from_uom_id = self.env['product.template'].sudo()._get_weight_uom_id_from_ir_config_parameter()
        to_uom_id = self.env.ref('uom.product_uom_gram') if grams else self.env.ref('uom.product_uom_kgm')
        if reverse:
            from_uom_id, to_uom_id = to_uom_id, from_uom_id
        if float_is_zero(weight, precision_rounding=from_uom_id.rounding):
            return weight
        return from_uom_id._compute_quantity(weight, to_uom_id)

    def sendcloud_convert_length(self, length, reverse=False, unit="cm"):
        """
            Each API request for sendcloud usually requires length in centimeters but also supports millimeters and meters.\n
            Length sent to Sendcloud must be of type integer as Sendcloud doesn't support floating numbers in its API.
            :param delivery.carrier self: the Sendcloud delivery carrier
            :param float length: the original length in the user default's UoM
            :param bool reverse: reverse the source and destination units of the conversion, default to False
            :param str unit: The destination unit, default to "cm", can also be "mm" or "m"
            :return: The converted length rounded up as an integer
            :rtype: int
            :raises UserError: if 'unit' is not in ("mm", "cm", "m")
        """
        if length == 0:
            return length
        length_uom_id = self.env['product.template'].sudo()._get_length_uom_id_from_ir_config_parameter()
        dest_uom_id = self.env['uom.uom'].search([('name', 'ilike', unit)])
        if not dest_uom_id:
            raise UserError(_("There's no unit of measure with the name \"%s\".", (unit)))
        if dest_uom_id == length_uom_id:
            return length
        elif reverse:
            dest_uom_id, length_uom_id = length_uom_id, dest_uom_id
        converted_length = length_uom_id._compute_quantity(length, dest_uom_id)
        converted_length = int(float_round(converted_length, precision_rounding=1.0, rounding_method='UP'))
        return converted_length

    def _set_sendcloud_products(self, shipping_product, return_product):
        self.ensure_one()
        # delete old shipping product since it will be replaced
        # self.sendcloud_shipping_id.unlink()
        products_to_create = [{
            'name': shipping_product['name'],
            'sendcloud_code': shipping_product['code'],
            'carrier': shipping_product['carrier'],
            'min_weight': shipping_product['weight_range']['min_weight'],
            'max_weight': shipping_product['weight_range']['max_weight'],
            'functionalities': shipping_product['local_cache']['functionalities'],
        }]
        if return_product:
            # self.sendcloud_return_id.sudo().unlink()
            products_to_create.append({
                'name': return_product['name'],
                'sendcloud_code': return_product['code'],
                'carrier': return_product['carrier'],
                'min_weight': return_product['weight_range']['min_weight'],
                'max_weight': return_product['weight_range']['max_weight'],
                'functionalities': return_product['local_cache']['functionalities'],
            })
        products = self.env['sendcloud.shipping.product'].create(products_to_create)
        if return_product:
            self.sendcloud_shipping_id = products[0]
            self.sendcloud_return_id = products[1]
        else:
            self.sendcloud_shipping_id = products
            self.sendcloud_return_id = False
        self.sendcloud_product_functionalities = {}
        if not self.sendcloud_can_batch_shipping:
            self.sendcloud_use_batch_shipping = False
        return True

    def raise_redirect_message(self):
        self.ensure_one()
        message = _('You must have a shipping product configured!')

        if self.sendcloud_shipping_id:
            message = _("The shipping product actually configured can't handle this delivery")
        raise RedirectWarning(
            message,
            {
                'type': 'ir.actions.act_window',
                'res_model': 'delivery.carrier',
                'res_id': self.id,
                'views': [[False, 'form']],
            },
            _('Go to the shipping product'),
        )

    @api.depends("delivery_type")
    def _compute_country_id(self):
        for dc in self:
            country = self.env['res.country']
            if dc.delivery_type == 'sendcloud':
                if dc.country_id:
                    continue
                company = dc.company_id or self.env.company
                default_warehouse = self.env.user.with_company(company.id)._get_default_warehouse_id()
                if default_warehouse:
                    country = default_warehouse.partner_id.country_id
                if not country and company.country_id:
                    country = company.country_id
                dc.country_id = country

    def _get_sendcloud(self):
        return SendCloud(self.sudo().sendcloud_public_key, self.sudo().sendcloud_secret_key, self.log_xml)

    def _prepare_track_message_docs(self, picking, parcels, sendcloud):
        docs = []
        parcel_ids = {}
        parcel_tracking_numbers = []
        for parcel in parcels:
            parcel_ids.setdefault(parcel['colli_uuid'], []).append(parcel['id'])
            parcel_tracking_numbers.append(parcel.get('tracking_number'))
            # this will include documents to print such as label
            # https://api.sendcloud.dev/docs/sendcloud-public-api/parcel-documents/operations/get-a-parcel-document
            # sendcloud docs mention there are 7 doc types
            # so we limit the loop to 7 docs
            for doc in parcel['documents'][:7]:
                doc_content = sendcloud._get_document(doc['link'])
                if doc['type'].lower() == 'label':
                    doc_title = f"{self._get_delivery_label_prefix()}-{parcel['id']}.pdf"
                else:
                    doc_type = doc['type'].capitalize()
                    doc_title = f"{self._get_delivery_doc_prefix()}-{doc_type}-{parcel['id']}.pdf"
                docs.append({
                    'name': doc_title,
                    'type': 'binary',
                    'raw': doc_content,
                    'res_model': picking._name,
                    'res_id': picking.id
                })
        doc_ids = self.env['ir.attachment'].create(docs)

        return list(parcel_ids.values()), parcel_tracking_numbers, doc_ids

    def _get_delivery_type(self):
        """ Override of delivery to return the sendcloud delivery type."""
        res = super()._get_delivery_type()
        if self.delivery_type != 'sendcloud':
            return res
        return self.sendcloud_shipping_id.carrier
