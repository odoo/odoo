# -*- coding: utf-8 -*-

import json
import requests
from werkzeug.urls import url_quote, url_quote_plus

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.addons.base.models.ir_qweb import keep_query
from odoo.addons.l10n_mx_edi.models.l10n_mx_edi_document import CANCELLATION_REASON_SELECTION, CFDI_DATE_FORMAT

MAPBOX_GEOCODE_URL = 'https://api.mapbox.com/geocoding/v5/mapbox.places/'
MAPBOX_MATRIX_URL = 'https://api.mapbox.com/directions-matrix/v1/mapbox/driving/'


class Picking(models.Model):
    _inherit = 'stock.picking'

    l10n_mx_edi_is_cfdi_needed = fields.Boolean(
        compute='_compute_l10n_mx_edi_is_cfdi_needed',
        store=True,
    )
    l10n_mx_edi_document_ids = fields.One2many(
        comodel_name='l10n_mx_edi.document',
        inverse_name='picking_id',
        copy=False,
        readonly=True,
    )
    l10n_mx_edi_cfdi_state = fields.Selection(
        string="CFDI status",
        selection=[
            ('sent', 'Signed'),
            ('cancel', 'Cancelled'),
        ],
        store=True,
        copy=False,
        tracking=True,
        compute="_compute_l10n_mx_edi_cfdi_state_and_attachment",
    )
    l10n_mx_edi_cfdi_sat_state = fields.Selection(
        string="SAT status",
        selection=[
            ('valid', "Validated"),
            ('not_found', "Not Found"),
            ('not_defined', "Not Defined"),
            ('cancelled', "Cancelled"),
            ('error', "Error"),
        ],
        store=True,
        copy=False,
        tracking=True,
        compute="_compute_l10n_mx_edi_cfdi_state_and_attachment",
    )
    l10n_mx_edi_cfdi_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        store=True,
        copy=False,
        compute='_compute_l10n_mx_edi_cfdi_state_and_attachment',
    )
    l10n_mx_edi_update_sat_needed = fields.Boolean(compute='_compute_l10n_mx_edi_update_sat_needed')
    l10n_mx_edi_external_trade = fields.Char(compute='_compute_l10n_mx_edi_external_trade')
    l10n_mx_edi_cfdi_uuid = fields.Char(
        string="Fiscal Folio",
        compute='_compute_l10n_mx_edi_cfdi_uuid',
        copy=False,
        store=True,
        help="Folio in electronic invoice, is returned by SAT when send to stamp.",
    )
    l10n_mx_edi_cfdi_origin = fields.Char(
        string='CFDI Origin',
        copy=False,
        help="Specify the existing Fiscal Folios to replace. Prepend with '04|'",
    )
    l10n_mx_edi_cfdi_cancel_picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string="Substituted By",
        compute='_compute_l10n_mx_edi_cfdi_cancel_picking_id',
    )

    l10n_mx_edi_src_lat = fields.Float(
        string='Source Latitude',
        related='picking_type_id.warehouse_id.partner_id.partner_latitude')
    l10n_mx_edi_src_lon = fields.Float(
        string='Source Longitude',
        related='picking_type_id.warehouse_id.partner_id.partner_longitude')
    l10n_mx_edi_des_lat = fields.Float(
        string='Destination Latitude',
        related='partner_id.partner_latitude')
    l10n_mx_edi_des_lon = fields.Float(
        string='Destination Longitude',
        related='partner_id.partner_longitude')
    l10n_mx_edi_distance = fields.Integer('Distance to Destination (KM)', copy=False)

    l10n_mx_edi_transport_type = fields.Selection(
        selection=[
            ('00', 'No Federal Highways'),
            ('01', 'Federal Transport'),
        ],
        string='Transport Type',
        copy=False,
        help='Specify the transportation method. The Delivery Guide will contain the Complemento Carta Porte only when'
             ' federal transport is used')
    l10n_mx_edi_vehicle_id = fields.Many2one(
        comodel_name='l10n_mx_edi.vehicle',
        string='Vehicle Setup',
        ondelete='restrict',
        copy=False,
        help='The vehicle used for Federal Transport')

    def _l10n_mx_edi_get_extra_picking_report_values(self):
        self.ensure_one()
        cfdi_infos = self.env['l10n_mx_edi.document']._decode_cfdi_attachment(self.l10n_mx_edi_cfdi_attachment_id.raw)

        barcode_value_params = keep_query(
            id=cfdi_infos['uuid'],
            re=cfdi_infos['supplier_rfc'],
            rr=cfdi_infos['customer_rfc'],
            tt=cfdi_infos['amount_total'],
        )
        barcode_sello = url_quote_plus(cfdi_infos['sello'][-8:], safe='=/').replace('%2B', '+')
        barcode_value = url_quote_plus(f'https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx?{barcode_value_params}&fe={barcode_sello}')
        barcode_src = f'/report/barcode/?barcode_type=QR&value={barcode_value}&width=180&height=180'

        return {
            **cfdi_infos,
            'barcode_src': barcode_src,
        }

    def _get_mail_thread_data_attachments(self):
        # EXTENDS 'stock'
        return super()._get_mail_thread_data_attachments() \
            - self.l10n_mx_edi_document_ids.attachment_id \
            + self.l10n_mx_edi_cfdi_attachment_id

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('company_id', 'state', 'picking_type_code')
    def _compute_l10n_mx_edi_is_cfdi_needed(self):
        for picking in self:
            picking.l10n_mx_edi_is_cfdi_needed = \
                picking.country_code == 'MX' \
                and picking.state == 'done' \
                and picking.picking_type_code == 'outgoing'

    @api.depends('l10n_mx_edi_document_ids.state', 'l10n_mx_edi_document_ids.sat_state')
    def _compute_l10n_mx_edi_cfdi_state_and_attachment(self):
        for picking in self:
            picking.l10n_mx_edi_cfdi_sat_state = picking.l10n_mx_edi_cfdi_sat_state
            picking.l10n_mx_edi_cfdi_state = None
            picking.l10n_mx_edi_cfdi_attachment_id = None
            for doc in picking.l10n_mx_edi_document_ids.sorted():
                if doc.state == 'picking_sent':
                    picking.l10n_mx_edi_cfdi_sat_state = doc.sat_state
                    picking.l10n_mx_edi_cfdi_state = 'sent'
                    picking.l10n_mx_edi_cfdi_attachment_id = doc.attachment_id
                    break
                elif doc.state == 'picking_cancel':
                    picking.l10n_mx_edi_cfdi_sat_state = doc.sat_state
                    picking.l10n_mx_edi_cfdi_state = 'cancel'
                    picking.l10n_mx_edi_cfdi_attachment_id = doc.attachment_id
                    break

    @api.depends('l10n_mx_edi_document_ids.state')
    def _compute_l10n_mx_edi_update_sat_needed(self):
        for picking in self:
            picking.l10n_mx_edi_update_sat_needed = bool(
                picking.l10n_mx_edi_document_ids.filtered_domain(
                    expression.OR(self.env['l10n_mx_edi.document']._get_update_sat_status_domains(from_cron=False))
                )
            )

    @api.depends('l10n_mx_edi_cfdi_attachment_id')
    def _compute_l10n_mx_edi_cfdi_uuid(self):
        for picking in self:
            if picking.l10n_mx_edi_cfdi_attachment_id:
                cfdi_infos = self.env['l10n_mx_edi.document']._decode_cfdi_attachment(picking.l10n_mx_edi_cfdi_attachment_id.raw)
                picking.l10n_mx_edi_cfdi_uuid = cfdi_infos.get('uuid')
            else:
                picking.l10n_mx_edi_cfdi_uuid = None

    @api.depends('partner_id')
    def _compute_l10n_mx_edi_external_trade(self):
        for picking in self:
            picking.l10n_mx_edi_external_trade = picking.partner_id.country_code != 'MX'

    @api.depends('l10n_mx_edi_cfdi_uuid')
    def _compute_l10n_mx_edi_cfdi_cancel_picking_id(self):
        for picking in self:
            if picking.company_id and picking.l10n_mx_edi_cfdi_uuid:
                picking.l10n_mx_edi_cfdi_cancel_picking_id = picking.search(
                    [
                        ('l10n_mx_edi_cfdi_origin', '=like', f'04|{picking.l10n_mx_edi_cfdi_uuid}%'),
                        ('company_id', '=', picking.company_id.id)
                    ],
                    limit=1,
                )
            else:
                picking.l10n_mx_edi_cfdi_cancel_picking_id = None

    # -------------------------------------------------------------------------
    # CFDI: Generation
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_cfdi_check_external_trade_config(self):
        """ Comex Features (Exports) have been extracted to l10n_mx_edi_stock_extended.
        This method suggests the module installation when trying to generate a delivery guide for an export country.
        """
        self.ensure_one()
        errors = []
        if self.l10n_mx_edi_external_trade:
            errors.append(_("The Delivery Guide is only available for shipping in MX. You might want to install comex features"))
        return errors

    def _l10n_mx_edi_cfdi_check_picking_config(self):
        """ Check the configuration of the picking. """
        self.ensure_one()
        errors = []
        if not self.l10n_mx_edi_transport_type:
            errors.append(_("You must select a transport type to generate the delivery guide"))
        if self.move_line_ids.product_id.filtered(lambda product: not product.unspsc_code_id):
            errors.append(_("All products require a UNSPSC Code"))
        if self.l10n_mx_edi_transport_type == '01' and not self.l10n_mx_edi_distance:
            errors.append(_("Distance in KM must be specified when using federal transport"))
        return errors

    def _l10n_mx_edi_add_picking_cfdi_values(self, cfdi_values):
        self.ensure_one()
        company = cfdi_values['company']

        if self.picking_type_id.warehouse_id.partner_id:
            cfdi_values['issued_address'] = self.picking_type_id.warehouse_id.partner_id
        issued_address = cfdi_values['issued_address']

        self.env['l10n_mx_edi.document']._add_base_cfdi_values(cfdi_values)
        self.env['l10n_mx_edi.document']._add_currency_cfdi_values(cfdi_values, company.currency_id)
        self.env['l10n_mx_edi.document']._add_document_name_cfdi_values(cfdi_values, self.name)
        self.env['l10n_mx_edi.document']._add_document_origin_cfdi_values(cfdi_values, self.l10n_mx_edi_cfdi_origin)
        self.env['l10n_mx_edi.document']._add_customer_cfdi_values(cfdi_values, self.partner_id)

        mx_tz = issued_address._l10n_mx_edi_get_cfdi_timezone()

        cfdi_values.update({
            'record': self,
            'cfdi_date': self.date_done.astimezone(mx_tz).strftime(CFDI_DATE_FORMAT),
            'scheduled_date': self.scheduled_date.astimezone(mx_tz).strftime(CFDI_DATE_FORMAT),
            'lugar_expedicion': issued_address.zip,
            'moves': self.move_ids.filtered(lambda ml: ml.quantity > 0),
            'weight_uom': self.env['product.template']._get_weight_uom_id_from_ir_config_parameter(),
        })

    @api.model
    def _l10n_mx_edi_prepare_picking_cfdi_template(self):
        return 'l10n_mx_edi_stock.cfdi_cartaporte'

    # -------------------------------------------------------------------------
    # CFDI: DOCUMENTS
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_cfdi_document_sent_failed(self, error, cfdi_filename=None, cfdi_str=None):
        """ Create/update the invoice document for 'sent_failed'.
        The parameters are provided by '_l10n_mx_edi_prepare_picking_cfdi'.

        :param error:           The error.
        :param cfdi_filename:   The optional filename of the cfdi.
        :param cfdi_str:        The optional content of the cfdi.
        """
        self.ensure_one()

        document_values = {
            'picking_id': self.id,
            'state': 'picking_sent_failed',
            'sat_state': None,
            'message': error,
        }
        if cfdi_filename and cfdi_str:
            document_values['attachment_id'] = {
                'name': cfdi_filename,
                'raw': cfdi_str,
            }
        return self.env['l10n_mx_edi.document']._create_update_picking_document(self, document_values)

    def _l10n_mx_edi_cfdi_document_sent(self, cfdi_filename, cfdi_str):
        """ Create/update the invoice document for 'sent'.
        The parameters are provided by '_l10n_mx_edi_prepare_picking_cfdi'.

        :param cfdi_filename:   The filename of the cfdi.
        :param cfdi_str:        The content of the cfdi.
        """
        self.ensure_one()

        document_values = {
            'picking_id': self.id,
            'state': 'picking_sent',
            'sat_state': 'not_defined',
            'message': None,
            'attachment_id': {
                'name': cfdi_filename,
                'raw': cfdi_str,
                'res_model': self._name,
                'res_id': self.id,
                'description': "CFDI",
            },
        }
        return self.env['l10n_mx_edi.document']._create_update_picking_document(self, document_values)

    def _l10n_mx_edi_cfdi_document_cancel_failed(self, error, cfdi, cancel_reason):
        """ Create/update the invoice document for 'cancel_failed'.

        :param error:           The error.
        :param cfdi:            The source cfdi attachment to cancel.
        :param cancel_reason:   The reason for this cancel.
        :return:                The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'picking_id': self.id,
            'state': 'picking_cancel_failed',
            'sat_state': None,
            'message': error,
            'attachment_id': cfdi.attachment_id.id,
            'cancellation_reason': cancel_reason,
        }
        return self.env['l10n_mx_edi.document']._create_update_picking_document(self, document_values)

    def _l10n_mx_edi_cfdi_document_cancel(self, cfdi, cancel_reason):
        """ Create/update the invoice document for 'cancel'.

        :param cfdi:            The source cfdi attachment to cancel.
        :param cancel_reason:   The reason for this cancel.
        :return:                The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'picking_id': self.id,
            'state': 'picking_cancel',
            'sat_state': 'not_defined',
            'message': None,
            'attachment_id': cfdi.attachment_id.id,
            'cancellation_reason': cancel_reason,
        }
        return self.env['l10n_mx_edi.document']._create_update_picking_document(self, document_values)

    # -------------------------------------------------------------------------
    # CFDI: FLOWS
    # -------------------------------------------------------------------------

    def l10n_mx_edi_cfdi_try_send(self):
        """ Try to generate and send the CFDI for the current picking. """
        self.ensure_one()

        # == Check the config ==
        errors = self._l10n_mx_edi_cfdi_check_external_trade_config() \
                 + self._l10n_mx_edi_cfdi_check_picking_config()
        if errors:
            self._l10n_mx_edi_cfdi_document_sent_failed("\n".join(errors))
            return

        # == Lock ==
        self.env['l10n_mx_edi.document']._with_locked_records(self)

        # == Send ==
        def on_populate(cfdi_values):
            self._l10n_mx_edi_add_picking_cfdi_values(cfdi_values)

        def on_failure(error, cfdi_filename=None, cfdi_str=None):
            self._l10n_mx_edi_cfdi_document_sent_failed(error, cfdi_filename=cfdi_filename, cfdi_str=cfdi_str)

        def on_success(_cfdi_values, cfdi_filename, cfdi_str, populate_return=None):
            document = self._l10n_mx_edi_cfdi_document_sent(cfdi_filename, cfdi_str)
            self.message_post(
                body=_("The CFDI document was successfully created and signed by the government."),
                attachment_ids=document.attachment_id.ids,
            )

        qweb_template = self._l10n_mx_edi_prepare_picking_cfdi_template()
        cfdi_filename = f'CFDI_DeliveryGuide_{self.name}.xml'.replace('/', '')
        self.env['l10n_mx_edi.document']._send_api(
            self.company_id,
            qweb_template,
            cfdi_filename,
            on_populate,
            on_failure,
            on_success,
        )

    def _l10n_mx_edi_cfdi_post_cancel(self):
        """ Cancel the current picking and drop a message in the chatter.
        This method is only there to unify the flows since they are multiple
        ways to cancel a picking:
        - The user can request a cancellation from Odoo.
        - The user can cancel the picking from the SAT, then update the SAT state in Odoo.
        """
        self.ensure_one()
        self.message_post(body=_("The CFDI document has been successfully cancelled."))

    def _l10n_mx_edi_cfdi_try_cancel(self, document):
        """ Try to cancel the CFDI for the current picking.

        :param document: The source payment document to cancel.
        """
        self.ensure_one()
        if self.l10n_mx_edi_cfdi_state != 'sent':
            return

        # == Lock ==
        self.env['l10n_mx_edi.document']._with_locked_records(self)

        # == Cancel ==
        substitution_doc = document._get_substitution_document()
        cancel_uuid = substitution_doc.attachment_uuid
        cancel_reason = '01' if cancel_uuid else '02'

        def on_failure(error):
            self._l10n_mx_edi_cfdi_document_cancel_failed(error, document, cancel_reason)

        def on_success():
            self._l10n_mx_edi_cfdi_document_cancel(document, cancel_reason)
            self.l10n_mx_edi_cfdi_origin = f'04|{self.l10n_mx_edi_cfdi_uuid}'
            self._l10n_mx_edi_cfdi_post_cancel()

        document._cancel_api(self.company_id, cancel_reason, on_failure, on_success)

    def l10n_mx_edi_cfdi_try_cancel(self):
        """ Try to cancel the CFDI for the current picking. """
        self.ensure_one()
        source_document = self.l10n_mx_edi_document_ids.filtered(lambda x: x.state == 'picking_sent')[:1]
        self._l10n_mx_edi_cfdi_try_cancel(source_document)

    def _l10n_mx_edi_cfdi_update_sat_state(self, document, sat_state, error=None):
        """ Update the SAT state of the document for the current picking.

        :param document:    The CFDI document to be updated.
        :param sat_state:   The newly fetched state from the SAT
        :param error:       In case of error, the message returned by the SAT.
        """
        self.ensure_one()

        # The user manually cancelled the document in the SAT portal.
        if document.state == 'picking_sent' and sat_state == 'cancelled':
            if document.sat_state not in ('valid', 'cancelled', 'skip'):
                document.sat_state = 'skip'

            document = self._l10n_mx_edi_cfdi_document_cancel(
                document,
                CANCELLATION_REASON_SELECTION[1][0],  # Force '02'.
            )
            document.sat_state = sat_state
            self._l10n_mx_edi_cfdi_post_cancel()
        else:
            document.sat_state = sat_state

        document.message = None
        if sat_state == 'error' and error:
            document.message = error
            self.message_post(body=error)

    def l10n_mx_edi_cfdi_try_sat(self):
        self.ensure_one()
        documents = self.l10n_mx_edi_document_ids
        for document in documents.filtered_domain(documents._get_update_sat_status_domain(from_cron=False)):
            document._update_sat_state()

    # -------------------------------------------------------------------------
    # MAPBOX
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_request_mapbox(self, url, params):
        try:
            fetched_data = requests.get(url, params=params, timeout=10)
        except Exception:
            raise UserError(_('Unable to connect to mapbox'))
        return fetched_data

    def l10n_mx_edi_action_set_partner_coordinates(self):
        mb_token = self.env['ir.config_parameter'].sudo().get_param('web_map.token_map_box', False)
        if not mb_token:
            raise UserError(_('Please configure MapBox to use this feature'))
        for record in self:
            src = record.picking_type_id.warehouse_id.partner_id.contact_address_complete
            dest = record.partner_id.contact_address_complete
            if not (src and dest):
                raise UserError(_('The warehouse address and the delivery address are required'))
            src_address = url_quote(src)
            url = f'{MAPBOX_GEOCODE_URL}{src_address}.json?'
            fetched_data = record._l10n_mx_edi_request_mapbox(url, {'access_token': mb_token})
            res = json.loads(fetched_data.content)
            if 'features' in res:
                record.picking_type_id.warehouse_id.partner_id.partner_latitude = res['features'][0]['geometry']['coordinates'][0]
                record.picking_type_id.warehouse_id.partner_id.partner_longitude = res['features'][0]['geometry']['coordinates'][1]
            dest_address = url_quote(dest)
            url = f'{MAPBOX_GEOCODE_URL}{dest_address}.json?'
            fetched_data = record._l10n_mx_edi_request_mapbox(url, {'access_token': mb_token})
            res = json.loads(fetched_data.content)
            if 'features' in res:
                record.partner_id.partner_latitude = res['features'][0]['geometry']['coordinates'][0]
                record.partner_id.partner_longitude = res['features'][0]['geometry']['coordinates'][1]

    def l10n_mx_edi_action_calculate_distance(self):
        mb_token = self.env['ir.config_parameter'].sudo().get_param('web_map.token_map_box', False)
        if not mb_token:
            raise UserError(_('Please configure MapBox to use this feature'))
        params = {
            'sources': 0,
            'destinations': 'all',
            'annotations': 'distance',
            'access_token': mb_token,
        }
        for record in self:
            if record.l10n_mx_edi_src_lat and record.l10n_mx_edi_src_lon \
                and record.l10n_mx_edi_des_lat and record.l10n_mx_edi_des_lon:
                url = f'{MAPBOX_MATRIX_URL}{record.l10n_mx_edi_src_lat},{record.l10n_mx_edi_src_lon};{record.l10n_mx_edi_des_lat},{record.l10n_mx_edi_des_lon}'
                fetched_data = record._l10n_mx_edi_request_mapbox(url, params)
                res = json.loads(fetched_data.content)
                if 'distances' in res:
                    record.l10n_mx_edi_distance = res['distances'][0][1] // 1000
            else:
                raise UserError(_('Distance calculation requires both the source and destination coordinates'))
