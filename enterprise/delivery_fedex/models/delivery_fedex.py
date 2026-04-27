# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import time

from markupsafe import Markup
from odoo.tools.zeep.helpers import serialize_object

from odoo import api, models, fields, _, tools
from odoo.exceptions import UserError
from odoo.tools import pdf, float_repr, format_list
from odoo.tools.safe_eval import const_eval

from .fedex_request import FedexRequest, _convert_curr_iso_fdx, _convert_curr_fdx_iso


_logger = logging.getLogger(__name__)


FEDEX_STOCK_TYPE = [
    ('PAPER_4X6', 'PAPER_4X6'),
    ('PAPER_4X6.75', 'PAPER_4X6.75'),
    ('PAPER_4X8', 'PAPER_4X8'),
    ('PAPER_4X9', 'PAPER_4X9'),
    ('PAPER_7X4.75', 'PAPER_7X4.75'),
    ('PAPER_8.5X11_BOTTOM_HALF_LABEL', 'PAPER_8.5X11_BOTTOM_HALF_LABEL'),
    ('PAPER_8.5X11_TOP_HALF_LABEL', 'PAPER_8.5X11_TOP_HALF_LABEL'),
    ('PAPER_LETTER', 'PAPER_LETTER'),
    ('STOCK_4X6', 'STOCK_4X6'),
    ('STOCK_4X6.75', 'STOCK_4X6.75'),
    ('STOCK_4X6.75_LEADING_DOC_TAB', 'STOCK_4X6.75_LEADING_DOC_TAB'),
    ('STOCK_4X6.75_TRAILING_DOC_TAB', 'STOCK_4X6.75_TRAILING_DOC_TAB'),
    ('STOCK_4X8', 'STOCK_4X8'),
    ('STOCK_4X9', 'STOCK_4X9'),
    ('STOCK_4X9_LEADING_DOC_TAB', 'STOCK_4X9_LEADING_DOC_TAB'),
    ('STOCK_4X9_TRAILING_DOC_TAB', 'STOCK_4X9_TRAILING_DOC_TAB')
]

HELP_EXTRA_DATA = """The extra data in FedEx is organized like the inside of a json file.
This functionality is advanced/technical and should only be used if you know what you are doing.

Example of valid value: ```
"ShipmentDetails": {"Pieces": {"Piece": {"AdditionalInformation": "extra info"}}}
```

With the above example, the AdditionalInformation of each piece will be updated.
More info on https://www.fedex.com/en-us/developer/web-services/process.html#documentation"""


class ProviderFedex(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[
        ('fedex', "FedEx (Legacy)")
    ], ondelete={'fedex': lambda recs: recs.write({'delivery_type': 'fixed', 'fixed_price': 0})})

    fedex_developer_key = fields.Char(string="Developer Key", groups="base.group_system")
    fedex_developer_password = fields.Char(string="Password", groups="base.group_system")
    fedex_account_number = fields.Char(string="FedEx Legacy Account Number", groups="base.group_system")
    fedex_meter_number = fields.Char(string="Meter Number", groups="base.group_system")
    fedex_droppoff_type = fields.Selection([('BUSINESS_SERVICE_CENTER', 'BUSINESS_SERVICE_CENTER'),
                                            ('DROP_BOX', 'DROP_BOX'),
                                            ('REGULAR_PICKUP', 'REGULAR_PICKUP'),
                                            ('REQUEST_COURIER', 'REQUEST_COURIER'),
                                            ('STATION', 'STATION')],
                                           string="Fedex Drop-Off Type",
                                           default='REGULAR_PICKUP')
    fedex_default_package_type_id = fields.Many2one('stock.package.type', string="Fedex Package Type")
    fedex_service_type = fields.Selection([('INTERNATIONAL_ECONOMY', 'INTERNATIONAL_ECONOMY'),
                                           ('INTERNATIONAL_PRIORITY', 'INTERNATIONAL_PRIORITY'),
                                           ('FEDEX_INTERNATIONAL_PRIORITY', 'FEDEX_INTERNATIONAL_PRIORITY'),
                                           ('FEDEX_INTERNATIONAL_PRIORITY_EXPRESS', 'FEDEX_INTERNATIONAL_PRIORITY_EXPRESS'),
                                           ('FEDEX_GROUND', 'FEDEX_GROUND'),
                                           ('FEDEX_2_DAY', 'FEDEX_2_DAY'),
                                           ('FEDEX_2_DAY_AM', 'FEDEX_2_DAY_AM'),
                                           ('FEDEX_3_DAY_FREIGHT', 'FEDEX_3_DAY_FREIGHT'),
                                           ('FIRST_OVERNIGHT', 'FIRST_OVERNIGHT'),
                                           ('PRIORITY_OVERNIGHT', 'PRIORITY_OVERNIGHT'),
                                           ('STANDARD_OVERNIGHT', 'STANDARD_OVERNIGHT'),
                                           ('FEDEX_NEXT_DAY_EARLY_MORNING', 'FEDEX_NEXT_DAY_EARLY_MORNING'),
                                           ('FEDEX_NEXT_DAY_MID_MORNING', 'FEDEX_NEXT_DAY_MID_MORNING'),
                                           ('FEDEX_NEXT_DAY_AFTERNOON', 'FEDEX_NEXT_DAY_AFTERNOON'),
                                           ('FEDEX_NEXT_DAY_END_OF_DAY', 'FEDEX_NEXT_DAY_END_OF_DAY'),
                                           ('FEDEX_EXPRESS_SAVER', 'FEDEX_EXPRESS_SAVER'),
                                           ('FEDEX_REGIONAL_ECONOMY', 'FEDEX_REGIONAL_ECONOMY'),
                                           ('FEDEX_FIRST', 'FEDEX_FIRST'),
                                           ('FEDEX_PRIORITY_EXPRESS', 'FEDEX_PRIORITY_EXPRESS'),
                                           ('FEDEX_PRIORITY', 'FEDEX_PRIORITY'),
                                           ('FEDEX_PRIORITY_EXPRESS_FREIGHT', 'FEDEX_PRIORITY_EXPRESS_FREIGHT'),
                                           ('FEDEX_PRIORITY_FREIGHT', 'FEDEX_PRIORITY_FREIGHT'),
                                           ('FEDEX_ECONOMY_SELECT', 'FEDEX_ECONOMY_SELECT'),
                                           ('FEDEX_INTERNATIONAL_CONNECT_PLUS', 'FEDEX_INTERNATIONAL_CONNECT_PLUS'),
                                           ],
                                          default='FEDEX_INTERNATIONAL_PRIORITY')
    fedex_duty_payment = fields.Selection([('SENDER', 'Sender'), ('RECIPIENT', 'Recipient')], required=True, default="SENDER")
    fedex_weight_unit = fields.Selection([('LB', 'LB'),
                                          ('KG', 'KG')],
                                         default='LB')
    # Note about weight units: Odoo (v9) currently works with kilograms.
    # --> Gross weight of each products are expressed in kilograms.
    # For some services, FedEx requires weights expressed in pounds, so we
    # convert them when necessary.
    fedex_label_stock_type = fields.Selection(FEDEX_STOCK_TYPE, string='Label Type', default='PAPER_LETTER')
    fedex_label_file_type = fields.Selection([('PDF', 'PDF'),
                                              ('EPL2', 'EPL2'),
                                              ('PNG', 'PNG'),
                                              ('ZPLII', 'ZPLII')],
                                             default='PDF', string="FEDEX Label File Type")
    fedex_document_stock_type = fields.Selection(FEDEX_STOCK_TYPE, string='Commercial Invoice Type', default='PAPER_LETTER')
    fedex_saturday_delivery = fields.Boolean(string="FedEx Saturday Delivery", help="""Special service:Saturday Delivery, can be requested on following days.
                                                                                 Thursday:\n1.FEDEX_2_DAY.\nFriday:\n1.PRIORITY_OVERNIGHT.\n2.FIRST_OVERNIGHT.
                                                                                 3.INTERNATIONAL_PRIORITY.\n(To Select Countries)""")
    fedex_extra_data_rate_request = fields.Text('Extra data for rate (legacy)', help=HELP_EXTRA_DATA)
    fedex_extra_data_ship_request = fields.Text('Extra data for ship (legacy)', help=HELP_EXTRA_DATA)
    fedex_extra_data_return_request = fields.Text('Extra data for return (legacy)', help=HELP_EXTRA_DATA)

    def _compute_can_generate_return(self):
        super(ProviderFedex, self)._compute_can_generate_return()
        for carrier in self:
            if not carrier.can_generate_return:
                if carrier.delivery_type == 'fedex':
                    carrier.can_generate_return = True

    def _compute_supports_shipping_insurance(self):
        res = super(ProviderFedex, self)._compute_supports_shipping_insurance()
        for carrier in self:
            if carrier.delivery_type == 'fedex':
                carrier.supports_shipping_insurance = True
        return res

    @api.onchange('fedex_service_type')
    def on_change_fedex_service_type(self):
        self.fedex_saturday_delivery = False

    def fedex_rate_shipment(self, order):
        is_india = order.partner_shipping_id.country_id.code == 'IN' and order.company_id.partner_id.country_id.code == 'IN'

        order_currency = order.currency_id
        superself = self.sudo()

        # Authentication stuff
        srm = FedexRequest(self.log_xml, request_type="rating", prod_environment=self.prod_environment)
        srm.web_authentication_detail(superself.fedex_developer_key, superself.fedex_developer_password)
        srm.client_detail(superself.fedex_account_number, superself.fedex_meter_number)

        # Build basic rating request and set addresses
        srm.transaction_detail(order.name)
        srm.shipment_request(
            self.fedex_droppoff_type,
            self.fedex_service_type,
            self.fedex_default_package_type_id.shipper_package_code,
            self.fedex_weight_unit,
            self.fedex_saturday_delivery,
        )

        srm.set_currency(_convert_curr_iso_fdx(order_currency.name))
        srm.set_shipper(order.company_id.partner_id, order.warehouse_id.partner_id)
        srm.set_recipient(order.partner_shipping_id)

        packages = self._get_packages_from_order(order, self.fedex_default_package_type_id)

        for sequence, package in enumerate(packages, 1):
            srm.add_package(
                self,
                package,
                _convert_curr_iso_fdx(package.company_id.currency_id.name),
                sequence_number=sequence,
                mode='rating'
            )

        weight_value = self._fedex_convert_weight(order._get_estimated_weight(), self.fedex_weight_unit)
        srm.set_master_package(weight_value, 1)

        # Commodities for customs declaration (international shipping)
        if 'INTERNATIONAL' in self.fedex_service_type or self.fedex_service_type == 'FEDEX_REGIONAL_ECONOMY' or is_india:
            commodities = self._get_commodities_from_order(order)
            for commodity in commodities:
                srm.commodities(self, commodity, _convert_curr_iso_fdx(order_currency.name))

            total_commodities_amount = sum(c.monetary_value * c.qty for c in commodities)
            srm.customs_value(_convert_curr_iso_fdx(order_currency.name), total_commodities_amount, "NON_DOCUMENTS")
            srm.duties_payment(order.warehouse_id.partner_id, superself.fedex_account_number, superself.fedex_duty_payment)

        # Prepare the request
        self._fedex_update_srm(srm, 'rate', order=order)
        del srm.ClientDetail['Region']
        request = serialize_object(dict(WebAuthenticationDetail=srm.WebAuthenticationDetail,
                                        ClientDetail=srm.ClientDetail,
                                        TransactionDetail=srm.TransactionDetail,
                                        VersionId=srm.VersionId,
                                        RequestedShipment=srm.RequestedShipment))
        self._fedex_add_extra_data_to_request(request, 'rate')
        response = srm.rate(request)

        warnings = response.get('warnings_message')
        if warnings:
            _logger.info(warnings)

        if response.get('errors_message'):
            return {'success': False,
                    'price': 0.0,
                    'error_message': _('Error:\n%s', response['errors_message']),
                    'warning_message': False}

        price = self._get_request_price(response['price'], order, order_currency)
        return {'success': True,
                'price': price,
                'error_message': False,
                'warning_message': _('Warning:\n%s', warnings) if warnings else False}

    def fedex_send_shipping(self, pickings):
        res = []

        for picking in pickings:
            order_currency = picking.sale_id.currency_id or picking.company_id.currency_id

            srm = FedexRequest(self.log_xml, request_type="shipping", prod_environment=self.prod_environment)
            superself = self.sudo()
            srm.web_authentication_detail(superself.fedex_developer_key, superself.fedex_developer_password)
            srm.client_detail(superself.fedex_account_number, superself.fedex_meter_number)

            srm.transaction_detail(picking.id)

            packages = picking.move_line_ids.result_package_id
            package_type = packages and packages[0].package_type_id.shipper_package_code or self.fedex_default_package_type_id.shipper_package_code
            srm.shipment_request(self.fedex_droppoff_type, self.fedex_service_type, package_type, self.fedex_weight_unit, self.fedex_saturday_delivery)
            srm.set_currency(_convert_curr_iso_fdx(order_currency.name))
            srm.set_shipper(picking.company_id.partner_id, picking.picking_type_id.warehouse_id.partner_id)
            srm.set_recipient(picking.partner_id)

            srm.shipping_charges_payment(superself.fedex_account_number)

            srm.shipment_label('COMMON2D', self.fedex_label_file_type, self.fedex_label_stock_type, 'TOP_EDGE_OF_TEXT_FIRST', 'SHIPPING_LABEL_FIRST')

            order = picking.sale_id

            net_weight = self._fedex_convert_weight(picking.shipping_weight, self.fedex_weight_unit)

            # Commodities for customs declaration (international shipping)
            if 'INTERNATIONAL' in self.fedex_service_type or self.fedex_service_type == 'FEDEX_REGIONAL_ECONOMY' or (picking.partner_id.country_id.code == 'IN' and picking.picking_type_id.warehouse_id.partner_id.country_id.code == 'IN'):

                commodities = self._get_commodities_from_stock_move_lines(picking.move_line_ids)
                for commodity in commodities:
                    srm.commodities(self, commodity, _convert_curr_iso_fdx(order_currency.name))

                total_commodities_amount = sum(c.monetary_value * c.qty for c in commodities)
                srm.customs_value(_convert_curr_iso_fdx(order_currency.name), total_commodities_amount, "NON_DOCUMENTS")
                srm.duties_payment(order.warehouse_id.partner_id, superself.fedex_account_number, superself.fedex_duty_payment)

                send_etd = superself.env['ir.config_parameter'].get_param("delivery_fedex.send_etd")
                srm.commercial_invoice(self.fedex_document_stock_type, send_etd)

            package_count = len(picking.move_line_ids.result_package_id) or 1

            # For india picking courier is not accepted without this details in label.
            po_number = order.display_name or False
            dept_number = False
            if picking.partner_id.country_id.code == 'IN' and picking.picking_type_id.warehouse_id.partner_id.country_id.code == 'IN':
                po_number = 'B2B' if picking.partner_id.commercial_partner_id.is_company else 'B2C'
                dept_number = 'BILL D/T: SENDER'

            # TODO RIM master: factorize the following crap

            packages = self._get_packages_from_picking(picking, self.fedex_default_package_type_id)

            # Note: Fedex has a complex multi-piece shipping interface
            # - Each package has to be sent in a separate request
            # - First package is called "master" package and holds shipping-
            #   related information, including addresses, customs...
            # - Last package responses contains shipping price and code
            # - If a problem happens with a package, every previous package
            #   of the shipping has to be cancelled separately
            # (Why doing it in a simple way when the complex way exists??)

            master_tracking_id = False
            package_labels = []
            carrier_tracking_refs = []
            lognote_pickings = picking.sale_id.picking_ids if picking.sale_id else picking

            for sequence, package in enumerate(packages, start=1):

                srm.add_package(
                    self,
                    package,
                    _convert_curr_iso_fdx(package.company_id.currency_id.name),
                    sequence_number=sequence,
                    po_number=po_number,
                    dept_number=dept_number,
                    reference=picking.display_name,
                )
                srm.set_master_package(net_weight, len(packages), master_tracking_id=master_tracking_id)

                # Prepare the request
                self._fedex_update_srm(srm, 'ship', picking=picking)
                request = serialize_object(dict(WebAuthenticationDetail=srm.WebAuthenticationDetail,
                                                ClientDetail=srm.ClientDetail,
                                                TransactionDetail=srm.TransactionDetail,
                                                VersionId=srm.VersionId,
                                                RequestedShipment=srm.RequestedShipment))
                self._fedex_add_extra_data_to_request(request, 'ship')
                response = srm.process_shipment(request)

                warnings = response.get('warnings_message')
                if warnings:
                    _logger.info(warnings)

                if response.get('errors_message'):
                    raise UserError(response['errors_message'])

                package_name = package.name or 'package-' + str(sequence)
                package_labels.append((package_name, srm.get_label()))
                carrier_tracking_refs.append(response['tracking_number'])

                # First package
                if sequence == 1:
                    master_tracking_id = response['master_tracking_id']

                # Last package
                if sequence == package_count:

                    carrier_price = self._get_request_price(response['price'], order, order_currency)

                    logmessage = Markup(_("Shipment created into Fedex<br/>"
                                          "<b>Tracking Numbers:</b> %(tracking_numbers)s<br/>"
                                          "<b>Packages:</b> %(packages)s",
                                          tracking_numbers=format_list(self.env, carrier_tracking_refs),
                                          packages=format_list(self.env, [pl[0] for pl in package_labels])))
                    if self.fedex_label_file_type != 'PDF':
                        attachments = [('%s-%s.%s' % (self._get_delivery_label_prefix(), pl[0], self.fedex_label_file_type), pl[1]) for pl in package_labels]
                    if self.fedex_label_file_type == 'PDF':
                        attachments = [('%s.pdf' % (self._get_delivery_label_prefix()), pdf.merge_pdf([pl[1] for pl in package_labels]))]
                    for pick in lognote_pickings:
                        pick.message_post(body=logmessage, attachments=attachments)
                    shipping_data = {'exact_price': carrier_price,
                                     'tracking_number': ','.join(carrier_tracking_refs)}
                    res = res + [shipping_data]

            # TODO RIM handle if a package is not accepted (others should be deleted)

            if self.return_label_on_delivery:
                self.get_return_label(picking, tracking_number=response['tracking_number'], origin_date=response['date'])
            commercial_invoice = srm.get_document()
            if commercial_invoice:
                fedex_documents = [('%s.pdf' % self._get_delivery_doc_prefix(), commercial_invoice)]
                for pick in lognote_pickings:
                    pick.message_post(body=_('Fedex Documents'), attachments=fedex_documents)
        return res

    def fedex_get_return_label(self, picking, tracking_number=None, origin_date=None):
        srm = FedexRequest(self.log_xml, request_type="shipping", prod_environment=self.prod_environment)
        superself = self.sudo()
        srm.web_authentication_detail(superself.fedex_developer_key, superself.fedex_developer_password)
        srm.client_detail(superself.fedex_account_number, superself.fedex_meter_number)

        srm.transaction_detail(picking.id)

        packages = picking.move_line_ids.result_package_id
        package_type = packages and packages[0].package_type_id.shipper_package_code or self.fedex_default_package_type_id.shipper_package_code
        srm.shipment_request(self.fedex_droppoff_type, self.fedex_service_type, package_type, self.fedex_weight_unit, self.fedex_saturday_delivery)
        srm.set_currency(_convert_curr_iso_fdx(picking.company_id.currency_id.name))
        srm.set_shipper(picking.partner_id, picking.partner_id)
        srm.set_recipient(picking.company_id.partner_id)

        srm.shipping_charges_payment(superself.fedex_account_number)

        srm.shipment_label('COMMON2D', self.fedex_label_file_type, self.fedex_label_stock_type, 'TOP_EDGE_OF_TEXT_FIRST', 'SHIPPING_LABEL_FIRST')
        if picking.is_return_picking:
            net_weight = self._fedex_convert_weight(picking._get_estimated_weight(), self.fedex_weight_unit)
        else:
            net_weight = self._fedex_convert_weight(picking.shipping_weight, self.fedex_weight_unit)
        package_type = packages[:1].package_type_id or picking.carrier_id.fedex_default_package_type_id
        order = picking.sale_id
        po_number = order.display_name or False
        dept_number = False
        packages = self._get_packages_from_picking(picking, self.fedex_default_package_type_id)
        for pkg in packages:
            srm.add_package(self, pkg, _convert_curr_iso_fdx(pkg.company_id.currency_id.name), reference=picking.display_name, po_number=po_number, dept_number=dept_number)
        srm.set_master_package(net_weight, 1)
        if 'INTERNATIONAL' in self.fedex_service_type or self.fedex_service_type == 'FEDEX_REGIONAL_ECONOMY' or (picking.partner_id.country_id.code == 'IN' and picking.picking_type_id.warehouse_id.partner_id.country_id.code == 'IN'):

            order_currency = picking.sale_id.currency_id or picking.company_id.currency_id

            commodities = [com for pack in packages for com in pack.commodities]
            for commodity in commodities:
                srm.commodities(self, commodity, _convert_curr_iso_fdx(order_currency.name))

            total_commodities_amount = sum(com.monetary_value * com.qty for com in commodities)
            srm.customs_value(_convert_curr_iso_fdx(order_currency.name), total_commodities_amount, "NON_DOCUMENTS")
            srm.duties_payment(order.warehouse_id.partner_id, superself.fedex_account_number, superself.fedex_duty_payment)

            srm.customs_value(_convert_curr_iso_fdx(order_currency.name), total_commodities_amount, "NON_DOCUMENTS")
            # We consider that returns are always paid by the company creating the label
            srm.duties_payment(picking.picking_type_id.warehouse_id.partner_id, superself.fedex_account_number, 'SENDER')
        srm.return_label(tracking_number, origin_date)

        # Prepare the request
        self._fedex_update_srm(srm, 'return', picking=picking)
        request = serialize_object(dict(WebAuthenticationDetail=srm.WebAuthenticationDetail,
                                        ClientDetail=srm.ClientDetail,
                                        TransactionDetail=srm.TransactionDetail,
                                        VersionId=srm.VersionId,
                                        RequestedShipment=srm.RequestedShipment))
        self._fedex_add_extra_data_to_request(request, 'return')
        response = srm.process_shipment(request)
        if not response.get('errors_message'):
            fedex_labels = [('%s-%s-%s.%s' % (self.get_return_label_prefix(), response['tracking_number'], index, self.fedex_label_file_type), label)
                            for index, label in enumerate(srm._get_labels(self.fedex_label_file_type))]
            picking.message_post(body=_('Return Label'), attachments=fedex_labels)
        else:
            raise UserError(response['errors_message'])

    def fedex_get_tracking_link(self, picking):
        return 'https://www.fedex.com/apps/fedextrack/?action=track&trackingnumber=%s' % picking.carrier_tracking_ref

    def fedex_cancel_shipment(self, picking):
        request = FedexRequest(self.log_xml, request_type="shipping", prod_environment=self.prod_environment)
        superself = self.sudo()
        request.web_authentication_detail(superself.fedex_developer_key, superself.fedex_developer_password)
        request.client_detail(superself.fedex_account_number, superself.fedex_meter_number)
        request.transaction_detail(picking.id)

        master_tracking_id = picking.carrier_tracking_ref.split(',')[0]
        request.set_deletion_details(master_tracking_id)
        serialized_request = serialize_object(dict(WebAuthenticationDetail=request.WebAuthenticationDetail,
                                                   ClientDetail=request.ClientDetail,
                                                   TransactionDetail=request.TransactionDetail,
                                                   VersionId=request.VersionId,
                                                   TrackingId=request.TrackingId,
                                                   DeletionControl=request.DeletionControl))
        result = request.delete_shipment(serialized_request)

        warnings = result.get('warnings_message')
        if warnings:
            _logger.info(warnings)

        if result.get('delete_success') and not result.get('errors_message'):
            picking.message_post(body=_(u'Shipment #%s has been cancelled', master_tracking_id))
            picking.write({'carrier_tracking_ref': '',
                           'carrier_price': 0.0})
        else:
            raise UserError(result['errors_message'])

    def _get_request_price(self, req_price, order, order_currency=None):
        """Extract price info in target currency, converting if necessary"""
        if not order_currency:
            order_currency = order.currency_id
        company = order.company_id or self.env.user.company_id
        fdx_currency = _convert_curr_iso_fdx(order_currency.name)
        if fdx_currency in req_price:
            # normally we'll have the order currency on the response, then we can take it as is
            return req_price[fdx_currency]
        _logger.info("Preferred currency has not been found in FedEx response")
        # otherwise, see if we have the company currency, and convert to the order's currency
        fdx_currency = _convert_curr_iso_fdx(company.currency_id.name)
        if fdx_currency in req_price:
            return company.currency_id._convert(
                req_price[fdx_currency], order_currency, company, order.date_order or fields.Date.today())
        # finally, attempt to find active currency in the database
        currency_codes = list(req_price.keys())
        # note, fedex sometimes return the currency as ISO instead of using their own code
        # (eg it can return GBP instead of UKL for a UK address)
        # so we'll do the search for both
        currency_codes += [_convert_curr_fdx_iso(c) for c in currency_codes]
        currency_instances = self.env['res.currency'].search([('name', 'in', currency_codes)])
        currency_by_name = {c.name: c for c in currency_instances}
        for fdx_currency in req_price:
            if fdx_currency in currency_by_name:
                return currency_by_name[fdx_currency]._convert(
                    req_price[fdx_currency], order_currency, company, order.date_order or fields.Date.today())
        _logger.info("No known currency has not been found in FedEx response")
        return 0.0

    def _fedex_add_extra_data_to_request(self, request, request_type):
        """Adds the extra data to the request.
        When there are multiple items in a list, they will all be affected by
        the change.
        for example, with
        {"ShipmentDetails": {"Pieces": {"Piece": {"AdditionalInformation": "extra info"}}}}
        the AdditionalInformation of each piece will be updated.
        """
        extra_data_input = {
            'rate': self.fedex_extra_data_rate_request,
            'ship': self.fedex_extra_data_ship_request,
            'return': self.fedex_extra_data_return_request,
        }.get(request_type) or ''
        try:
            extra_data = const_eval('{' + extra_data_input + '}')
        except SyntaxError:
            raise UserError(_('Invalid syntax for FedEx extra data.'))

        def extra_data_to_request(request, extra_data):
            """recursive function that adds extra data to the current request."""
            for key, new_value in extra_data.items():
                request[key] = current_value = request.get(key)
                if isinstance(current_value, list):
                    for item in current_value:
                        extra_data_to_request(item, new_value)
                elif isinstance(new_value, dict) and isinstance(current_value, dict):
                    extra_data_to_request(current_value, new_value)
                else:
                    request[key] = new_value

        extra_data_to_request(request, extra_data)

    def _fedex_get_default_custom_package_code(self):
        return 'YOUR_PACKAGING'

    def _fedex_convert_weight(self, weight, unit='KG'):
        if unit == 'KG':
            convert_to = 'uom.product_uom_kgm'
        elif unit == 'LB':
            convert_to = 'uom.product_uom_lb'
        else:
            raise ValueError

        weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        new_value = weight_uom_id._compute_quantity(weight, self.env.ref(convert_to), round=False)

        # Some users may want to ship very lightweight items; in order to give them a rating, we round the
        # converted weight of the shipping to the smallest value accepted by FedEx: 0.01 kg or lb.
        # (in the case where the weight is actually 0.0 because weights are not set, don't do this)
        if weight > 0.0:
            new_value = max(new_value, 0.01)

        # Rounding to avoid differences between sum of values before and after conversion, caused by
        # Floating Point Arithmetic issues (ex: .1 + .1 + .1 != .3)
        return float_repr(new_value, 10)

    def _fedex_update_srm(self, srm, request_type, order=None, picking=None):
        """ Hook to introduce new custom behaviors in the Fedex request. """
        return srm
