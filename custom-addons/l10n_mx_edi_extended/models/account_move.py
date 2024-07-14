# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.tools.sql import column_exists, create_column
from odoo.tools import float_round

import re
from collections import defaultdict


CUSTOM_NUMBERS_PATTERN = re.compile(r'[0-9]{2}  [0-9]{2}  [0-9]{4}  [0-9]{7}')


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_mx_edi_external_trade = fields.Boolean(
        string="Need external trade?",
        readonly=False, store=True,
        compute='_compute_l10n_mx_edi_external_trade',
        help="If this field is active, the CFDI that generates this invoice will include the complement "
             "'External Trade'.")
    l10n_mx_edi_external_trade_type = fields.Selection(
        selection=[
            ('02', 'Definitive'),
            ('03', 'Temporary'),
        ],
        string="External Trade",
        readonly=False, store=True,
        compute='_compute_l10n_mx_edi_external_trade_type',
        help="If this field is 02, the CFDI will include the complement.")

    def _auto_init(self):
        """
        Create compute stored field l10n_mx_edi_external_trade
        here to avoid MemoryError on large databases.
        """
        if not column_exists(self.env.cr, 'account_move', 'l10n_mx_edi_external_trade'):
            create_column(self.env.cr, 'account_move', 'l10n_mx_edi_external_trade', 'boolean')
            # _compute_l10n_mx_edi_external_trade uses res_partner.l10n_mx_edi_external_trade,
            # which is a new field in this module hence all values set to False.
            self.env.cr.execute("UPDATE account_move set l10n_mx_edi_external_trade=FALSE;")
        if not column_exists(self.env.cr, 'account_move', 'l10n_mx_edi_external_trade_type'):
            create_column(self.env.cr, 'account_move', 'l10n_mx_edi_external_trade_type', 'varchar')
        return super()._auto_init()

    # -------------------------------------------------------------------------
    # CFDI: HELPERS
    # -------------------------------------------------------------------------

    @api.depends('l10n_mx_edi_external_trade_type')
    def _compute_l10n_mx_edi_external_trade(self):
        for move in self:
            move.l10n_mx_edi_external_trade = move.l10n_mx_edi_external_trade_type == '02'

    @api.depends('partner_id', 'partner_id.l10n_mx_edi_external_trade_type')
    def _compute_l10n_mx_edi_external_trade_type(self):
        for move in self:
            move.l10n_mx_edi_external_trade_type = move.partner_id.l10n_mx_edi_external_trade_type

    # -------------------------------------------------------------------------
    # CFDI
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_add_invoice_cfdi_values(self, cfdi_values, percentage_paid=None, global_invoice=False):
        # EXTENDS 'l10n_mx_edi'
        self.ensure_one()

        if self.journal_id.l10n_mx_address_issued_id:
            cfdi_values['issued_address'] = self.journal_id.l10n_mx_address_issued_id

        super()._l10n_mx_edi_add_invoice_cfdi_values(cfdi_values, percentage_paid=percentage_paid, global_invoice=global_invoice)
        if cfdi_values.get('errors'):
            return

        cfdi_values['exportacion'] = self.l10n_mx_edi_external_trade_type or '01'

        # External Trade
        ext_trade_values = cfdi_values['comercio_exterior'] = {}
        if self.l10n_mx_edi_external_trade_type == '02':

            # Customer.
            customer_values = cfdi_values['receptor']
            customer = customer_values['customer']
            if customer_values['rfc'] == 'XEXX010101000':
                cfdi_values['receptor']['num_reg_id_trib'] = customer.vat
                # A value must be registered in the ResidenciaFiscal field when information is registered in the
                # NumRegIdTrib field.
                cfdi_values['receptor']['residencia_fiscal'] = customer.country_id.l10n_mx_edi_code

            ext_trade_values['receptor'] = {
                **cfdi_values['receptor'],
                'curp': customer.l10n_mx_edi_curp,
                'calle': customer.street_name,
                'numero_exterior': customer.street_number,
                'numero_interior': customer.street_number2,
                'colonia': customer.l10n_mx_edi_colony_code,
                'localidad': customer.l10n_mx_edi_locality_id.code,
                'municipio': customer.city_id.l10n_mx_edi_code,
                'estado': customer.state_id.code,
                'pais': customer.country_id.l10n_mx_edi_code,
                'codigo_postal': customer.zip,
            }

            # Supplier.
            supplier_values = cfdi_values['emisor']
            supplier = supplier_values['supplier']
            ext_trade_values['emisor'] = {
                'curp': supplier.l10n_mx_edi_curp,
                'calle': supplier.street_name,
                'numero_exterior': supplier.street_number,
                'numero_interior': supplier.street_number2,
                'colonia': supplier.l10n_mx_edi_colony_code,
                'localidad': supplier.l10n_mx_edi_locality_id.code,
                'municipio': supplier.city_id.l10n_mx_edi_code,
                'estado': supplier.state_id.code,
                'pais': supplier.country_id.l10n_mx_edi_code,
                'codigo_postal': supplier.zip,
            }

            # Shipping.
            shipping = self.partner_shipping_id
            if shipping != customer:

                shipping_cfdi_values = dict(cfdi_values)
                # In case of COMEX we need to fill "NumRegIdTrib" with the real tax id of the customer
                # but let the generic RFC.
                self.env['l10n_mx_edi.document']._add_customer_cfdi_values(
                    shipping_cfdi_values,
                    customer=shipping,
                    usage=cfdi_values['receptor']['uso_cfdi'],
                    to_public=self.l10n_mx_edi_cfdi_to_public,
                )
                shipping_values = shipping_cfdi_values['receptor']
                if (
                    shipping.country_id == shipping.commercial_partner_id.country_id
                    and shipping_values['rfc'] == 'XEXX010101000'
                ):
                    shipping_vat = shipping.vat.strip() if shipping.vat else None
                else:
                    shipping_vat = None

                if shipping.country_id.l10n_mx_edi_code == 'MEX':
                    colony = shipping.l10n_mx_edi_colony_code
                    locality = shipping.l10n_mx_edi_locality_id.code
                    city = shipping.city_id.l10n_mx_edi_code
                else:
                    colony = shipping.l10n_mx_edi_colony
                    locality = shipping.l10n_mx_edi_locality
                    city = shipping.city

                if shipping.country_id.l10n_mx_edi_code in ('MEX', 'USA', 'CAN') or shipping.state_id.code:
                    state = shipping.state_id.code
                else:
                    state = 'NA'

                ext_trade_values['destinario'] = {
                    'num_reg_id_trib': shipping_vat,
                    'nombre': shipping.name,
                    'calle': shipping.street_name,
                    'numero_exterior': shipping.street_number,
                    'numero_interior': shipping.street_number2,
                    'colonia': colony,
                    'localidad': locality,
                    'municipio': city,
                    'estado': state,
                    'pais': shipping.country_id.l10n_mx_edi_code,
                    'codigo_postal': shipping.zip,
                }

            # Certificate.
            ext_trade_values['certificado_origen'] = '1' if self.l10n_mx_edi_cer_source else '0'
            ext_trade_values['num_certificado_origen'] = self.l10n_mx_edi_cer_source

            # Rate.
            mxn = self.env["res.currency"].search([('name', '=', 'MXN')], limit=1)
            usd = self.env["res.currency"].search([('name', '=', 'USD')], limit=1)
            ext_trade_values['tipo_cambio_usd'] = usd._get_conversion_rate(usd, mxn, self.company_id, self.date)
            if ext_trade_values['tipo_cambio_usd']:
                to_usd_rate = (cfdi_values['tipo_cambio'] or 1.0) / ext_trade_values['tipo_cambio_usd']
            else:
                to_usd_rate = 0.0

            # Misc.
            if customer.country_id in self.env.ref('base.europe').country_ids:
                ext_trade_values['numero_exportador_confiable'] = self.company_id.l10n_mx_edi_num_exporter
            else:
                ext_trade_values['numero_exportador_confiable'] = None
            ext_trade_values['incoterm'] = self.invoice_incoterm_id.code
            ext_trade_values['observaciones'] = self.narration

            # Details per product.
            product_values_map = defaultdict(lambda: {
                'quantity': 0.0,
                'price_unit': 0.0,
                'total': 0.0,
            })
            for line_vals in cfdi_values['conceptos_list']:
                line = line_vals['line']['record']
                product_values_map[line.product_id]['quantity'] += line.l10n_mx_edi_qty_umt
                product_values_map[line.product_id]['price_unit'] += line.l10n_mx_edi_price_unit_umt
                product_values_map[line.product_id]['total'] += line_vals['importe']
            ext_trade_values['total_usd'] = 0.0
            ext_trade_values['mercancia_list'] = []
            for product, product_values in product_values_map.items():
                total_usd = float_round(product_values['total'] * to_usd_rate, precision_digits=4)
                ext_trade_values['mercancia_list'].append({
                    'no_identificacion': product.default_code,
                    'fraccion_arancelaria': product.l10n_mx_edi_tariff_fraction_id.code,
                    'cantidad_aduana': product_values['quantity'],
                    'unidad_aduana': product.l10n_mx_edi_umt_aduana_id.l10n_mx_edi_code_aduana,
                    'valor_unitario_udana': float_round(product_values['price_unit'] * to_usd_rate, precision_digits=6),
                    'valor_dolares': total_usd,
                })
                ext_trade_values['total_usd'] += total_usd
        else:
            # Invoice lines.
            for line_vals in cfdi_values['conceptos_list']:
                line_vals['informacion_aduanera_list'] = line_vals['line']['record']._l10n_mx_edi_get_custom_numbers()

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_mx_edi_customs_number = fields.Char(
        help='Optional field for entering the customs information in the case '
        'of first-hand sales of imported goods or in the case of foreign trade'
        ' operations with goods or services.\n'
        'The format must be:\n'
        ' - 2 digits of the year of validation followed by two spaces.\n'
        ' - 2 digits of customs clearance followed by two spaces.\n'
        ' - 4 digits of the serial number followed by two spaces.\n'
        ' - 1 digit corresponding to the last digit of the current year, '
        'except in case of a consolidated customs initiated in the previous '
        'year of the original request for a rectification.\n'
        ' - 6 digits of the progressive numbering of the custom.',
        string='Customs number',
        copy=False)
    l10n_mx_edi_umt_aduana_id = fields.Many2one(
        comodel_name='uom.uom',
        string="UMT Aduana",
        readonly=True, store=True, compute_sudo=True,
        related='product_id.l10n_mx_edi_umt_aduana_id',
        help="Used in complement 'Comercio Exterior' to indicate in the products the TIGIE Units of Measurement. "
             "It is based in the SAT catalog.")
    l10n_mx_edi_qty_umt = fields.Float(
        string="Qty UMT",
        digits=(16, 3),
        readonly=False, store=True,
        compute='_compute_l10n_mx_edi_qty_umt',
        help="Quantity expressed in the UMT from product. It is used in the attribute 'CantidadAduana' in the CFDI")
    l10n_mx_edi_price_unit_umt = fields.Float(
        string="Unit Value UMT",
        readonly=True, store=True,
        compute='_compute_l10n_mx_edi_price_unit_umt',
        help="Unit value expressed in the UMT from product. It is used in the attribute 'ValorUnitarioAduana' in the "
             "CFDI")

    def _auto_init(self):
        if not column_exists(self.env.cr, "account_move_line", "l10n_mx_edi_umt_aduana_id"):
            create_column(self.env.cr, "account_move_line", "l10n_mx_edi_umt_aduana_id", "int4")
            # Since l10n_mx_edi_umt_aduana_id columns does not exist we can assume the columns
            # l10n_mx_edi_qty_umt and l10n_mx_edi_price_unit_umt do not exist either
            create_column(self.env.cr, "account_move_line", "l10n_mx_edi_qty_umt", "numeric")
            create_column(self.env.cr, "account_move_line", "l10n_mx_edi_price_unit_umt", "float8")
        return super()._auto_init()

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_get_custom_numbers(self):
        self.ensure_one()
        if self.l10n_mx_edi_customs_number:
            return [num.strip() for num in self.l10n_mx_edi_customs_number.split(',')]
        else:
            return []

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('l10n_mx_edi_umt_aduana_id', 'product_uom_id', 'quantity')
    def _compute_l10n_mx_edi_qty_umt(self):
        for line in self:
            product_aduana_code = line.l10n_mx_edi_umt_aduana_id.l10n_mx_edi_code_aduana
            uom_aduana_code = line.product_uom_id.l10n_mx_edi_code_aduana
            if product_aduana_code == uom_aduana_code:
                line.l10n_mx_edi_qty_umt = line.quantity
            elif '01' in (product_aduana_code or ''):
                line.l10n_mx_edi_qty_umt = line.product_id.weight * line.quantity
            else:
                line.l10n_mx_edi_qty_umt = None

    @api.depends('quantity', 'price_unit', 'l10n_mx_edi_qty_umt')
    def _compute_l10n_mx_edi_price_unit_umt(self):
        for line in self:
            if line.l10n_mx_edi_qty_umt:
                line.l10n_mx_edi_price_unit_umt = line.quantity * line.price_unit / line.l10n_mx_edi_qty_umt
            else:
                line.l10n_mx_edi_price_unit_umt = line.price_unit

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------

    @api.constrains('l10n_mx_edi_customs_number')
    def _check_l10n_mx_edi_customs_number(self):
        invalid_lines = self.env['account.move.line']
        for line in self:
            custom_numbers = line._l10n_mx_edi_get_custom_numbers()
            if any(not CUSTOM_NUMBERS_PATTERN.match(custom_number) for custom_number in custom_numbers):
                invalid_lines |= line

        if not invalid_lines:
            return

        raise ValidationError(_(
            "Custom numbers set on invoice lines are invalid and should have a pattern like: 15  48  3009  0001234:\n%(invalid_message)s",
            invalid_message='\n'.join('%s (id=%s)' % (line.l10n_mx_edi_customs_number, line.id) for line in invalid_lines),
        ))
