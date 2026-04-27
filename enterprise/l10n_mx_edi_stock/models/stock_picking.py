# -*- coding: utf-8 -*-

import json
import uuid

import requests
from werkzeug.urls import url_quote, url_quote_plus

from odoo import api, models, fields, _
from odoo.addons.base.models.ir_qweb import keep_query
from odoo.addons.l10n_mx_edi.models.l10n_mx_edi_document import CANCELLATION_REASON_SELECTION, CFDI_DATE_FORMAT
from odoo.exceptions import UserError
from odoo.osv import expression

from .product_template import MX_PACKAGING_CATALOG

MAPBOX_GEOCODE_URL = 'https://api.mapbox.com/geocoding/v5/mapbox.places/'
MAPBOX_MATRIX_URL = 'https://api.mapbox.com/directions-matrix/v1/mapbox/driving/'


class Picking(models.Model):
    _inherit = 'stock.picking'

    l10n_mx_edi_is_delivery_guide_needed = fields.Boolean(
        compute='_compute_l10n_mx_edi_is_delivery_guide_needed'
    )
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
    l10n_mx_edi_idccp = fields.Char(
        string="IdCCP",
        help="Additional UUID for the Delivery Guide.",
        compute='_compute_l10n_mx_edi_idccp',
    )
    l10n_mx_edi_gross_vehicle_weight = fields.Float(
        string="Gross Vehicle Weight",
        compute="_compute_l10n_mx_edi_gross_vehicle_weight",
        store=True,
        readonly=False,
    )
    l10n_mx_edi_customs_regime_ids = fields.Many2many(
        string="Customs Regimes",
        help="Regimes associated to the good's transfer (import or export).",
        comodel_name='l10n_mx_edi.customs.regime',
        ondelete='restrict',
    )
    l10n_mx_edi_customs_document_type_id = fields.Many2one(
        string="Customs Document Type",
        help="Type of customs document associated with the transport of the goods.",
        comodel_name='l10n_mx_edi.customs.document.type',
        ondelete="restrict",
    )
    l10n_mx_edi_customs_document_type_code = fields.Char(related='l10n_mx_edi_customs_document_type_id.code')
    l10n_mx_edi_pedimento_number = fields.Char(
        string="Pedimento Number",
        help="Pedimento number associated with the import of the goods.",
    )
    l10n_mx_edi_customs_doc_identification = fields.Char(
        string="Customs Document Identification",
        help="Folio of the customs document associated with the import of the goods.",
    )
    l10n_mx_edi_importer_id = fields.Many2one(
        string="Importer",
        help="Importer registered in the customs documentation.",
        comodel_name='res.partner',
        ondelete="restrict",
    )

    def _l10n_mx_edi_get_cartaporte_pdf_values(self):
        self.ensure_one()

        existing_cfdi_values = self.env['l10n_mx_edi.document']._decode_cfdi_attachment(self.l10n_mx_edi_cfdi_attachment_id.raw)
        cfdi_values = self.env['l10n_mx_edi.document']._get_company_cfdi_values(self.company_id)
        self.env['l10n_mx_edi.document']._add_certificate_cfdi_values(cfdi_values)
        self._l10n_mx_edi_add_picking_cfdi_values(cfdi_values)
        if existing_cfdi_values.get('carta_porte_idccp'):
            cfdi_values['idccp'] = existing_cfdi_values['carta_porte_idccp']

        warehouse_partner = self.picking_type_id.warehouse_id.partner_id

        figure_types_dict = dict(self.env['l10n_mx_edi.figure']._fields['type'].selection)
        vehicle_configs_dict = dict(self.env['l10n_mx_edi.vehicle']._fields['vehicle_config'].selection)
        transport_types_dict = dict(self.env['stock.picking']._fields['l10n_mx_edi_transport_type'].selection)

        ubicacion_fields = (
            'id_ubicacion',
            'rfc_remitente_destinatario',
            'num_reg_id_trib',
            'residencia_fiscal',
            'fecha_hora_salida_llegada'
        )

        origin_partner = self.partner_id if self.picking_type_code == 'incoming' else warehouse_partner
        destination_partner = self.partner_id if self.picking_type_code == 'outgoing' else warehouse_partner

        origen_domicilio = {
            field: value or "-" for field, value in cfdi_values['origen']['domicilio'].items()
        }
        destino_domicilio = {
            field: value or "-" for field, value in cfdi_values['destino']['domicilio'].items()
        }

        # Add legible data to the origin and destination addresses
        if origen_domicilio['municipio'] != origin_partner.city:
            origen_domicilio['municipio'] += f" - {origin_partner.city}"
        if origen_domicilio['estado'] != origin_partner.state_id.name:
            origen_domicilio['estado'] += f" - {origin_partner.state_id.name}"
        if origen_domicilio['pais'] != origin_partner.country_id.name:
            origen_domicilio['pais'] += f" - {origin_partner.country_id.name}"

        if destino_domicilio['municipio'] != destination_partner.city:
            destino_domicilio['municipio'] += f" - {destination_partner.city}"
        if destino_domicilio['estado'] != destination_partner.state_id.name:
            destino_domicilio['estado'] += f" - {destination_partner.state_id.name}"
        if destino_domicilio['pais'] != destination_partner.country_id.name:
            destino_domicilio['pais'] += f" - {destination_partner.country_id.name}"

        contains_hazardous_materials = any(self.move_ids.product_id.mapped('l10n_mx_edi_hazardous_material_code_id'))

        if self.l10n_mx_edi_external_trade:
            external_trade_vals = {
                'external_trade': True,
                'transp_internac': "Sí",
                'entrada_salida_merc': cfdi_values.get('entrada_salida_merc', "-"),
                'regimenes_aduanero': ", ".join(cfdi_values.get('regimenes_aduanero', ["-"])),
                'pais_origen_destino': f"{self.partner_id.country_id.l10n_mx_edi_code} - {self.partner_id.country_id.name}",
                'via_entrada_salida': f"{self.l10n_mx_edi_transport_type} - {transport_types_dict.get(self.l10n_mx_edi_transport_type, '')}",
            }
        else:
            external_trade_vals = {
                'external_trade': False,
                'transp_internac': "No",
            }

        # Generate QR code of the URL to access the service regarding the current guide document (legal requirement)
        barcode_value = url_quote_plus(f"https://verificacfdi.facturaelectronica.sat.gob.mx/verificaccp/default.aspx?"
                                       f"IdCCP={cfdi_values['idccp']}&"
                                       f"FechaOrig={cfdi_values['cfdi_date']}&"
                                       f"FechaTimb={cfdi_values['scheduled_date']}")
        barcode_src = f'/report/barcode/?barcode_type=QR&value={barcode_value}&width=180&height=180'

        return {
            **external_trade_vals,
            'idccp': cfdi_values['idccp'] or "-",
            'total_dist_recorrida': self.l10n_mx_edi_distance or "-",
            'peso_bruto_total': cfdi_values['format_float'](sum(self.move_ids.mapped('weight')), 3),
            'unidad_peso': cfdi_values['weight_uom'].unspsc_code_id.code or "-",
            'num_total_mercancias': len(self.move_ids),
            'origen_domicilio': origen_domicilio,
            'destino_domicilio': destino_domicilio,
            'origen_ubicacion': {
                field: cfdi_values['origen'][field] or "-" for field in ubicacion_fields
            },
            'destino_ubicacion': {
                field: cfdi_values['destino'][field] or "-" for field in (*ubicacion_fields, 'distancia_recorrida')
            },
            'transport_perm_sct': self.l10n_mx_edi_vehicle_id.transport_perm_sct or "-",
            'num_permiso_sct': self.l10n_mx_edi_vehicle_id.name or "-",
            'config_vehicular': f"{self.l10n_mx_edi_vehicle_id.vehicle_config} - {vehicle_configs_dict.get(self.l10n_mx_edi_vehicle_id.vehicle_config, '')}",
            'peso_bruto_vehicular': cfdi_values['peso_bruto_vehicular'] or "-",
            'placa_vm': self.l10n_mx_edi_vehicle_id.vehicle_licence or "-",
            'anio_modelo_vm': self.l10n_mx_edi_vehicle_id.vehicle_model or "-",
            'asegura_resp_civil': self.l10n_mx_edi_vehicle_id.transport_insurer or "-",
            'poliza_resp_civil': self.l10n_mx_edi_vehicle_id.transport_insurance_policy or "-",
            'asegura_med_ambiente': self.l10n_mx_edi_vehicle_id.environment_insurer if contains_hazardous_materials else "-",
            'poliza_med_ambiente': self.l10n_mx_edi_vehicle_id.environment_insurance_policy if contains_hazardous_materials else "-",
            'figures': [
                {
                    'tipo_figura': f"{figure.type} - {figure_types_dict.get(figure.type, '')}",
                    'num_licencia': (figure.type == '01' and figure.operator_id.l10n_mx_edi_operator_licence) or "-",
                    'num_reg_id_trib_figura': figure.operator_id.vat or "-"
                        if figure.operator_id.country_id.l10n_mx_edi_code != 'MEX'
                        else "-",
                    'residencia_fiscal_figura': f"{figure.operator_id.country_id.l10n_mx_edi_code} - {figure.operator_id.country_id.name}" or "-"
                        if figure.operator_id.country_id.l10n_mx_edi_code != 'MEX'
                        else "-",
                }
                for figure in self.l10n_mx_edi_vehicle_id.figure_ids.sorted('type')
            ],
            'barcode_src': barcode_src,
        }

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

    @api.model
    def _l10n_mx_edi_get_packaging_desc(self, code):
        return dict(MX_PACKAGING_CATALOG).get(code, None)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('company_id', 'picking_type_code')
    def _compute_l10n_mx_edi_is_delivery_guide_needed(self):
        for picking in self:
            picking.l10n_mx_edi_is_delivery_guide_needed = (
                picking.country_code == 'MX'
                and picking.picking_type_code in ('incoming', 'outgoing')
            )

    @api.depends('company_id', 'state', 'picking_type_code')
    def _compute_l10n_mx_edi_is_cfdi_needed(self):
        for picking in self:
            picking.l10n_mx_edi_is_cfdi_needed = (
                picking.l10n_mx_edi_is_delivery_guide_needed
                and picking.state == 'done'
            )

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

    @api.depends('l10n_mx_edi_is_cfdi_needed')
    def _compute_l10n_mx_edi_idccp(self):
        for picking in self:
            if picking.l10n_mx_edi_is_cfdi_needed and not picking.l10n_mx_edi_idccp:
                # The IdCCP must be a 36 characters long RFC 4122 identifier starting with 'CCC'.
                picking.l10n_mx_edi_idccp = f'CCC{str(uuid.uuid4())[3:]}'
            else:
                picking.l10n_mx_edi_idccp = False

    @api.depends('l10n_mx_edi_vehicle_id')
    def _compute_l10n_mx_edi_gross_vehicle_weight(self):
        for picking in self:
            if picking.l10n_mx_edi_vehicle_id and not picking.l10n_mx_edi_gross_vehicle_weight:
                picking.l10n_mx_edi_gross_vehicle_weight = picking.l10n_mx_edi_vehicle_id.gross_vehicle_weight
            else:
                picking.l10n_mx_edi_gross_vehicle_weight = picking.l10n_mx_edi_gross_vehicle_weight

    # -------------------------------------------------------------------------
    # CFDI: Generation
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_cfdi_check_external_trade_config(self):
        """ Check the configuration of the partner's address. """
        self.ensure_one()
        errors = []
        if not self.partner_id.zip or not self.partner_id.state_id:
            errors.append(_("A zip code and state are required to generate a delivery guide"))
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
        if self.l10n_mx_edi_vehicle_id and not self.l10n_mx_edi_gross_vehicle_weight:
            errors.append(_("Please define a gross vehicle weight."))

        if self.l10n_mx_edi_external_trade:
            if not self.l10n_mx_edi_customs_document_type_code:
                errors.append(_("Please define a customs regime."))
            # Code '01' corresponds to 'Pedimento'.
            if self.l10n_mx_edi_customs_document_type_code != '01' and not self.l10n_mx_edi_customs_doc_identification:
                errors.append(_("Please define a customs document identification."))
            if self.l10n_mx_edi_importer_id and not self.l10n_mx_edi_importer_id.vat:
                errors.append(_("Please define a VAT number for the importer '%s'.", self.l10n_mx_edi_importer_id.name))
            if any(not move.product_id.l10n_mx_edi_material_type for move in self.move_ids):
                errors.append(_("At least one product is missing a material type."))

        return errors

    def _l10n_mx_edi_add_picking_cfdi_values(self, cfdi_values):
        self.ensure_one()

        self.env['l10n_mx_edi.document']._add_base_cfdi_values(cfdi_values)
        self.env['l10n_mx_edi.document']._add_currency_cfdi_values(cfdi_values, cfdi_values['company'].currency_id)
        self.env['l10n_mx_edi.document']._add_document_name_cfdi_values(cfdi_values, self.name)
        self.env['l10n_mx_edi.document']._add_document_origin_cfdi_values(cfdi_values, self.l10n_mx_edi_cfdi_origin)
        self.env['l10n_mx_edi.document']._add_customer_cfdi_values(cfdi_values, self.partner_id)

        receptor = cfdi_values['receptor']
        emisor = cfdi_values['emisor']

        warehouse_partner = self.picking_type_id.warehouse_id.partner_id
        mx_tz = warehouse_partner._l10n_mx_edi_get_cfdi_timezone()

        cfdi_values.update({
            'record': self,
            'cfdi_date': self.date_done.astimezone(mx_tz).strftime(CFDI_DATE_FORMAT),
            'scheduled_date': self.scheduled_date.astimezone(mx_tz).strftime(CFDI_DATE_FORMAT),
            'lugar_expedicion': warehouse_partner.zip,
            'moves': self.move_ids.filtered(lambda ml: ml.quantity > 0),
            'weight_uom': self.env['product.template']._get_weight_uom_id_from_ir_config_parameter(),
        })

        cfdi_values['issued_address'] = warehouse_partner
        cfdi_values['idccp'] = self.l10n_mx_edi_idccp
        cfdi_values['origen'] = {
            'id_ubicacion': f"OR{str(self.location_id.id).rjust(6, '0')}",
            'fecha_hora_salida_llegada': cfdi_values['cfdi_date'],
            'num_reg_id_trib': None,
            'residencia_fiscal': None,
        }
        cfdi_values['destino'] = {
            'id_ubicacion': f"DE{str(self.location_dest_id.id).rjust(6, '0')}",
            'fecha_hora_salida_llegada': cfdi_values['scheduled_date'],
            'num_reg_id_trib': None,
            'residencia_fiscal': None,
            'distancia_recorrida': self.l10n_mx_edi_distance,
        }

        if self.l10n_mx_edi_vehicle_id:
            cfdi_values['peso_bruto_vehicular'] = self.l10n_mx_edi_gross_vehicle_weight
        else:
            cfdi_values['peso_bruto_vehicular'] = None

        if self.picking_type_code == 'outgoing':
            cfdi_values['destino']['rfc_remitente_destinatario'] = receptor['rfc']
            if warehouse_partner.country_id.l10n_mx_edi_code != 'MEX':
                cfdi_values['origen']['rfc_remitente_destinatario'] = 'XEXX010101000'
                cfdi_values['origen']['num_reg_id_trib'] = emisor['supplier'].vat
                cfdi_values['origen']['residencia_fiscal'] = warehouse_partner.country_id.l10n_mx_edi_code
            else:
                cfdi_values['origen']['rfc_remitente_destinatario'] = emisor['rfc']
            self._l10n_mx_edi_add_domicilio_cfdi_values(cfdi_values['origen'], warehouse_partner)
            self._l10n_mx_edi_add_domicilio_cfdi_values(cfdi_values['destino'], self.partner_id)
        else:
            cfdi_values['origen']['rfc_remitente_destinatario'] = receptor['rfc']
            if warehouse_partner.country_id.l10n_mx_edi_code != 'MEX':
                cfdi_values['destino']['rfc_remitente_destinatario'] = 'XEXX010101000'
                cfdi_values['destino']['num_reg_id_trib'] = emisor['supplier'].vat
                cfdi_values['destino']['residencia_fiscal'] = warehouse_partner.country_id.l10n_mx_edi_code
            else:
                cfdi_values['destino']['rfc_remitente_destinatario'] = emisor['rfc']
            self._l10n_mx_edi_add_domicilio_cfdi_values(cfdi_values['origen'], self.partner_id)
            self._l10n_mx_edi_add_domicilio_cfdi_values(cfdi_values['destino'], warehouse_partner)

        if self.l10n_mx_edi_external_trade:
            cfdi_values['tipo_documento'] = self.l10n_mx_edi_customs_document_type_code
            if self.picking_type_code == 'outgoing':
                cfdi_values['destino']['num_reg_id_trib'] = receptor['customer'].vat
                cfdi_values['destino']['residencia_fiscal'] = receptor['customer'].country_id.l10n_mx_edi_code
            else:  # picking_type_code in ('incoming', 'internal')
                cfdi_values['origen']['num_reg_id_trib'] = receptor['customer'].vat
                cfdi_values['origen']['residencia_fiscal'] = receptor['customer'].country_id.l10n_mx_edi_code
            if self.picking_type_code in ('outgoing', 'incoming'):
                cfdi_values['entrada_salida_merc'] = 'Salida' if self.picking_type_code == 'outgoing' else 'Entrada'
                cfdi_values['regimenes_aduanero'] = self.l10n_mx_edi_customs_regime_ids.mapped('code')

            # Code '01' corresponds to 'Pedimento'.
            if self.l10n_mx_edi_customs_document_type_code == '01':
                if self.picking_type_code == 'incoming':
                    cfdi_values['num_pedimento'] = self.l10n_mx_edi_pedimento_number
                    cfdi_values['rfc_impo'] = self.l10n_mx_edi_importer_id.vat
            else:
                cfdi_values['ident_doc_aduanero'] = self.l10n_mx_edi_customs_doc_identification

    @api.model
    def _l10n_mx_edi_add_domicilio_cfdi_values(self, cfdi_values, partner):
        cfdi_values['domicilio'] = {
            'calle': partner.street,
            'codigo_postal': partner.zip,
            'colonia': partner.l10n_mx_edi_colony_code,
            'estado': partner.state_id.code,
            'pais': partner.country_id.l10n_mx_edi_code,
            'municipio': partner.city_id.l10n_mx_edi_code or partner.city,
        }

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
        self.env['res.company']._with_locked_records(self)

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
        self.env['res.company']._with_locked_records(self)

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

    def l10n_mx_edi_action_print_cartaporte(self):
        return self.env.ref('l10n_mx_edi_stock.action_report_cartaporte').report_action(self)
