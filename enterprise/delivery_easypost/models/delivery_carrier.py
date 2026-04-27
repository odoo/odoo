# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import requests
from markupsafe import Markup
from werkzeug.urls import url_join

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round
from odoo.tools import file_open

from .easypost_request import EasypostRequest

class DeliverCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[
        ('easypost', 'Easypost')
    ], ondelete={'easypost': lambda recs: recs.write({'delivery_type': 'fixed', 'fixed_price': 0})})
    easypost_test_api_key = fields.Char("Test API Key", groups="base.group_system", help="Enter your API test key from Easypost account.")
    easypost_production_api_key = fields.Char("Production API Key", groups="base.group_system", help="Enter your API production key from Easypost account")
    easypost_delivery_type = fields.Char('Easypost Carrier Type')
    easypost_delivery_type_id = fields.Char('Easypost Carrier Type ID, technical for API request')
    easypost_default_package_type_id = fields.Many2one("stock.package.type", string="Default Package Type for Easypost", domain="[('easypost_carrier', '=', easypost_delivery_type)]")
    easypost_default_service_id = fields.Many2one("easypost.service", string="Default Service Level", help="If not set, the less expensive available service level will be chosen.", domain="[('easypost_carrier', '=', easypost_delivery_type)]")
    easypost_label_file_type = fields.Selection([
        ('PNG', 'PNG'), ('PDF', 'PDF'),
        ('ZPL', 'ZPL'), ('EPL2', 'EPL2')],
        string="Easypost Label File Type", default='PDF')
    easypost_insurance_fee_rate = fields.Float("Insurance fee rate (USD)")
    easypost_insurance_fee_minimum = fields.Float("Insurance fee minimum (USD)")

    def _compute_can_generate_return(self):
        super(DeliverCarrier, self)._compute_can_generate_return()
        for carrier in self:
            if carrier.delivery_type == 'easypost':
                carrier.can_generate_return = True

    def _compute_supports_shipping_insurance(self):
        res = super(DeliverCarrier, self)._compute_supports_shipping_insurance()
        for carrier in self:
            if carrier.delivery_type == 'easypost':
                carrier.supports_shipping_insurance = True
        return res

    def action_get_carrier_type(self):
        """ Return the list of carriers configured by the customer
        on its easypost account.
        """
        if self.delivery_type == 'easypost' and self.sudo().easypost_production_api_key:
            ep = EasypostRequest(self.sudo().easypost_production_api_key, self.log_xml)
            carriers = ep.fetch_easypost_carrier()
            if carriers:
                action = self.env["ir.actions.actions"]._for_xml_id("delivery_easypost.act_delivery_easypost_carrier_type")
                action['context'] = {
                    'carrier_types': carriers,
                    'default_delivery_carrier_id': self.id,
                }
                return action
        else:
            raise UserError(_('A production key is required in order to load your easypost carriers.'))

    def easypost_rate_shipment(self, order):
        """ Return the rates for a quotation/SO."""
        ep = EasypostRequest(self.sudo().easypost_production_api_key if self.prod_environment else self.sudo().easypost_test_api_key, self.log_xml)
        response = ep.rate_request(self, order.partner_shipping_id, order.warehouse_id.partner_id, order)
        # Return error message
        if response.get('error_message'):
            return {
                'success': False,
                'price': 0.0,
                'error_message': response.get('error_message'),
                'warning_message': False
            }

        # Update price with the order currency
        rate = response.get('rate')
        if order.currency_id.name == rate['currency']:
            price = float(rate['rate'])
        else:
            quote_currency = self.env['res.currency'].search([('name', '=', rate['currency'])], limit=1)
            price = quote_currency._convert(float(rate['rate']), order.currency_id, self.env.company, fields.Date.context_today(self))

        # Update price with the insurance cost
        insurance_cost = response.get('insurance_cost', 0)
        usd = self.env.ref('base.USD')
        price += usd._convert(insurance_cost, order.currency_id, self.env.company, fields.Date.context_today(self))

        return {
            'success': True,
            'price': price,
            'error_message': False,
            'warning_message': response.get('warning_message', False)
        }

    def easypost_send_shipping(self, pickings):
        """ It creates an easypost order and buy it with the selected rate on
        delivery method or cheapest rate if it is not set. It will use the
        packages used with the put in pack functionality or a single package if
        the user didn't use packages.
        Once the order is purchased. It will post as message the tracking
        links and the shipping labels.
        """
        res = []
        ep = EasypostRequest(self.sudo().easypost_production_api_key if self.prod_environment else self.sudo().easypost_test_api_key, self.log_xml)
        for picking in pickings:
            result = ep.send_shipping(self, picking.partner_id, picking.picking_type_id.warehouse_id.partner_id, picking=picking)
            if result.get('error_message'):
                raise UserError(result['error_message'])
            rate = result.get('rate')
            if rate['currency'] == picking.company_id.currency_id.name:
                price = float(rate['rate'])
            else:
                quote_currency = self.env['res.currency'].search([('name', '=', rate['currency'])], limit=1)
                price = quote_currency._convert(float(rate['rate']), picking.company_id.currency_id, self.env.company, fields.Date.context_today(self))

            # Update price with the insurance cost
            insurance_cost = result.get('insurance_cost', 0)
            usd = self.env.ref('base.USD')
            price += usd._convert(insurance_cost, picking.company_id.currency_id, self.env.company, fields.Date.context_today(self))

            # return tracking information
            carrier_tracking_link = ""
            for track_number, tracker_url in result.get('track_shipments_url').items():
                carrier_tracking_link += Markup("<a href='%s'>%s</a><br/>") % (tracker_url, track_number)

            carrier_tracking_ref = ' + '.join(result.get('track_shipments_url').keys())

            # pickings where we should leave a lognote
            lognote_pickings = picking.sale_id.picking_ids if picking.sale_id else picking
            requests_session = requests.Session()

            logmessage = Markup(_("Shipment created into Easypost<br/>"
                                  "<b>Tracking Numbers:</b> %s<br/>")) % (carrier_tracking_link)

            labels = []
            for track_number, label_url in result.get('track_label_data').items():
                try:
                    response = requests_session.get(label_url, timeout=30)
                    response.raise_for_status()
                    labels.append(('%s-%s.%s' % (self._get_delivery_label_prefix(), track_number, self.easypost_label_file_type), response.content))
                except Exception:
                    logmessage += Markup('<li><a href="%s">%s</a></li>') % (label_url, label_url)

            for pick in lognote_pickings:
                pick.message_post(body=logmessage, attachments=labels)

            logmessage = _('Easypost Documents:') + Markup("<br/>")

            forms = []
            for form_type, form_url in result.get('forms', {}).items():
                try:
                    response = requests_session.get(form_url, timeout=30)
                    response.raise_for_status()
                    forms.append(('%s-%s-%s' % (self._get_delivery_doc_prefix(), form_type, form_url.split('/')[-1]), response.content))
                except Exception:
                    logmessage += Markup('<li><a href="%s">%s</a></li>') % (form_url, form_url)

            if result.get('forms'):
                for pick in lognote_pickings:
                    pick.message_post(body=logmessage, attachments=forms)

            shipping_data = {'exact_price': price,
                             'tracking_number': carrier_tracking_ref}
            res = res + [shipping_data]
            # store order reference on picking
            picking.ep_order_ref = result.get('id')
            if picking.carrier_id.return_label_on_delivery:
                self.get_return_label(picking)
        return res

    def easypost_get_return_label(self, pickings, tracking_number=None, origin_date=None):
        ep = EasypostRequest(self.sudo().easypost_production_api_key if self.prod_environment else self.sudo().easypost_test_api_key, self.log_xml)
        result = ep.send_shipping(self, pickings.partner_id, pickings.picking_type_id.warehouse_id.partner_id, picking=pickings, is_return=True)
        if result.get('error_message'):
            raise UserError(result['error_message'])

        requests_session = requests.Session()
        logmessage = Markup(_('Return Label<br/>'))
        labels = []
        for track_number, label_url in result.get('track_label_data').items():
            try:
                response = requests_session.get(label_url, timeout=30)
                response.raise_for_status()
                labels.append(('%s-%s.%s' % (self.get_return_label_prefix(), track_number, self.easypost_label_file_type), response.content))
            except Exception:
                logmessage += Markup('<li><a href="%s">%s</a></li>') % (label_url, label_url)

        pickings.message_post(body=logmessage, attachments=labels)


    def easypost_get_tracking_link(self, picking):
        """ Returns the tracking links from a picking. Easypost reutrn one
        tracking link by package. It specific to easypost since other delivery
        carrier use a single link for all packages.
        """
        ep = EasypostRequest(self.sudo().easypost_production_api_key if self.prod_environment else self.sudo().easypost_test_api_key, self.log_xml)
        if picking.ep_order_ref:
            tracking_urls = ep.get_tracking_link(picking.ep_order_ref)
        else:
            tracking_urls = []
            for code in picking.carrier_tracking_ref.split('+'):
                tracking_urls += ep.get_tracking_link_from_code(code.strip())
        return len(tracking_urls) == 1 and tracking_urls[0][1] or json.dumps(tracking_urls)

    def easypost_cancel_shipment(self, pickings):
        # Note: Easypost API not provide shipment/order cancel mechanism
        raise UserError(_("You can't cancel Easypost shipping."))

    def _easypost_get_services_and_package_types(self):
        """ Get the list of services and package types by carrier
        type. They are stored in 2 dict stored in 2 distinct static json file.
        The dictionaries come from an easypost doc parsing since packages and
        services list are not available with an API request. The purpose of a
        json is to replace the static file request by an API request if easypost
        implements a way to do it.
        """
        packages = json.load(file_open('delivery_easypost/static/data/package_types_by_carriers.json'))
        services = json.load(file_open('delivery_easypost/static/data/services_by_carriers.json'))
        return packages, services

    @api.onchange('delivery_type')
    def _onchange_delivery_type(self):
        if self.delivery_type == 'easypost':
            self = self.sudo()
            if not self.easypost_test_api_key or not self.easypost_production_api_key:
                carrier = self.env['delivery.carrier'].search([('delivery_type', '=', 'easypost'), ('company_id', '=', self.env.company.id)], limit=1)
                if carrier.easypost_test_api_key and not self.easypost_test_api_key:
                    self.easypost_test_api_key = carrier.easypost_test_api_key
                if carrier.easypost_production_api_key and not self.easypost_production_api_key:
                    self.easypost_production_api_key = carrier.easypost_production_api_key

    def _easypost_set_insurance_fees(self):
        """ Sets the `easypost_insurance_fee_rate` and
        `easypost_insurance_fee_minimum` values.
        """
        if self.delivery_type == 'easypost' and self.sudo().easypost_production_api_key:
            ep = EasypostRequest(self.sudo().easypost_production_api_key, self.log_xml)
            user = ep.fetch_easypost_user()
            if user and user.get('insurance_fee_rate') and user.get('insurance_fee_minimum'):
                self.easypost_insurance_fee_rate = float(user.get('insurance_fee_rate'))
                self.easypost_insurance_fee_minimum = float(user.get('insurance_fee_minimum'))
            else:
                raise UserError(_('Unable to retrieve your default insurance rates.'))
        else:
            raise UserError(_('A production key is required in order to load your insurance fees.'))

    def _generate_services(self, rates):
        """ When a user do a rate request easypost returns
        a rates for each service available. However some services
        could not be guess before a first API call. This method
        complete the list of services for the used carrier type.
        """
        services_name = [rate.get('service') for rate in rates]
        existing_services = self.env['easypost.service'].search_read([
            ('name', 'in', services_name),
            ('easypost_carrier', '=', self.easypost_delivery_type)
        ], ["name"])
        for service_name in set([service['name'] for service in existing_services]) ^ set(services_name):
            self.env['easypost.service'].create({
                'name': service_name,
                'easypost_carrier': self.easypost_delivery_type
            })

    def _easypost_convert_weight(self, weight):
        """ Each API request for easypost required
        a weight in pounds.
        """
        if weight == 0:
            return weight
        weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        weight_in_pounds = weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_lb'))
        weigth_in_ounces = max(0.1, float_round((weight_in_pounds * 16), precision_digits=1))
        return weigth_in_ounces

    def _get_delivery_type(self):
        """ Override of delivery to return the easypost delivery type."""
        res = super()._get_delivery_type()
        if self.delivery_type != 'easypost':
            return res
        return self.easypost_delivery_type

    def _easypost_usd_insured_value(self, package_value, currency):
        """ With Easypost, To specify an amount to insure, pass the insurance
        attribute as a string. The currency of all insurance is USD.
        """
        if not self.shipping_insurance:
            return 0
        usd = self.env.ref('base.USD')
        current_insured_value = package_value * self.shipping_insurance / 100
        usd_insured_value = currency._convert(current_insured_value, usd, self.env.company, fields.Date.context_today(self))
        return usd_insured_value

    def _easypost_usd_estimated_insurance_cost(self, usd_insured_value):
        """ Returns the calculated insurance cost based on the user's
        insurance fees. This function should be called only if there is a
        shipping insurance.
        """
        self._easypost_set_insurance_fees()
        return max(usd_insured_value * self.easypost_insurance_fee_rate, self.easypost_insurance_fee_minimum)
