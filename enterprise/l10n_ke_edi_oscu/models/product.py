# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models
from odoo.tools.float_utils import json_float_round
from odoo.exceptions import UserError
from odoo.addons.l10n_ke_edi_oscu.models.account_move import format_etims_datetime
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

PRODUCT_TYPE_CODE_SELECTION = [('1', "Raw Material"), ('2', "Finished Product"), ('3', "Service")]


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    l10n_ke_packaging_unit_id = fields.Many2one(
        comodel_name='l10n_ke_edi_oscu.code',
        string="Packaging Unit",
        compute='_compute_l10n_ke_packaging_unit_id',
        inverse='_set_l10n_ke_packaging_unit_id',
        domain=[('code_type', '=', '17')],
        help="KRA code that describes the type of packaging used.",
    )
    l10n_ke_packaging_quantity = fields.Float(
        string="Package Quantity",
        compute='_compute_l10n_ke_packaging_quantity',
        inverse='_set_l10n_ke_packaging_quantity',
        help="Number of products in a package.",
    )
    l10n_ke_origin_country_id = fields.Many2one(
        comodel_name='res.country',
        string="Origin Country",
        compute='_compute_l10n_ke_origin_country_id',
        inverse='_set_l10n_ke_origin_country_id',
        help="The origin country of the product.",
    )
    l10n_ke_product_type_code = fields.Selection(
        string="eTIMS Product Type",
        selection=PRODUCT_TYPE_CODE_SELECTION,
        compute='_compute_l10n_ke_product_type_code',
        inverse='_set_l10n_ke_product_type_code',
        help="Used by eTIMS to determine the type of the product",
    )
    l10n_ke_is_insurance_applicable = fields.Boolean(
        string="Insurance Applicable",
        help="Check this box if the product is covered by insurance.",
        compute='_compute_l10n_ke_is_insurance_applicable',
        inverse='_set_l10n_ke_is_insurance_applicable',
    )
    l10n_ke_item_code = fields.Char(
        string="KRA Item Code",
        help="The code assigned to this product on eTIMS",
        compute='_compute_l10n_ke_item_code',
        search='_search_l10n_ke_item_code',
    )

    # === Computes === #

    def compute_is_storable(self):
        super().compute_is_storable()
        fiscal_country_codes = self.env.companies.mapped('account_fiscal_country_id.code')
        if 'KE' in fiscal_country_codes:
            self.filtered(lambda p: p.type == 'consu').is_storable = True

    @api.depends('product_variant_ids.l10n_ke_packaging_unit_id')
    def _compute_l10n_ke_packaging_unit_id(self):
        self._compute_template_field_from_variant_field('l10n_ke_packaging_unit_id')

    def _set_l10n_ke_packaging_unit_id(self):
        self._set_product_variant_field('l10n_ke_packaging_unit_id')

    @api.depends('product_variant_ids.l10n_ke_packaging_quantity')
    def _compute_l10n_ke_packaging_quantity(self):
        self._compute_template_field_from_variant_field('l10n_ke_packaging_quantity')

    def _set_l10n_ke_packaging_quantity(self):
        self._set_product_variant_field('l10n_ke_packaging_quantity')

    @api.depends('product_variant_ids.l10n_ke_origin_country_id')
    def _compute_l10n_ke_origin_country_id(self):
        self._compute_template_field_from_variant_field('l10n_ke_origin_country_id')

    def _set_l10n_ke_origin_country_id(self):
        self._set_product_variant_field('l10n_ke_origin_country_id')

    @api.depends('product_variant_ids.l10n_ke_product_type_code')
    def _compute_l10n_ke_product_type_code(self):
        self._compute_template_field_from_variant_field('l10n_ke_product_type_code')

    def _set_l10n_ke_product_type_code(self):
        self._set_product_variant_field('l10n_ke_product_type_code')

    @api.depends('product_variant_ids.l10n_ke_is_insurance_applicable')
    def _compute_l10n_ke_is_insurance_applicable(self):
        self._compute_template_field_from_variant_field('l10n_ke_is_insurance_applicable')

    def _set_l10n_ke_is_insurance_applicable(self):
        self._set_product_variant_field('l10n_ke_is_insurance_applicable')

    @api.depends('product_variant_ids.l10n_ke_item_code')
    def _compute_l10n_ke_item_code(self):
        self._compute_template_field_from_variant_field('l10n_ke_item_code')

    @api.model
    def _search_l10n_ke_item_code(self, operator, value):
        return [('product_variant_ids.l10n_ke_item_code', operator, value)]

    # === Actions === #

    def action_l10n_ke_oscu_save_item(self):
        if self.product_variant_count != 1:
            raise UserError(_("There should only be one product variant per product template!"))
        return self.product_variant_ids.action_l10n_ke_oscu_save_item()

    def action_l10n_ke_oscu_save_stock_master(self):
        if self.product_variant_count != 1:
            raise UserError(_("There should only be one product variant per product template!"))
        return self.product_variant_ids.action_l10n_ke_oscu_save_stock_master()

    def _get_related_fields_variant_template(self):
        # EXTENDS 'product'
        return [
            *super()._get_related_fields_variant_template(),
            'l10n_ke_packaging_unit_id',
            'l10n_ke_packaging_quantity',
            'l10n_ke_origin_country_id',
            'l10n_ke_product_type_code',
            'l10n_ke_is_insurance_applicable',
        ]


class ProductProduct(models.Model):
    _inherit = 'product.product'

    l10n_ke_packaging_unit_id = fields.Many2one(
        comodel_name='l10n_ke_edi_oscu.code',
        string="Packaging Unit",
        domain=[('code_type', '=', '17')],
        compute='_compute_l10n_ke_packaging_unit_id',
        store=True,
        readonly=False,
        help="KRA code that describes the type of packaging used.",
    )
    l10n_ke_packaging_quantity = fields.Float(
        string="Package Quantity",
        help="Number of products in a package.",
        default=1,
    )
    l10n_ke_origin_country_id = fields.Many2one(
        comodel_name='res.country',
        string="Origin Country",
        help="The origin country of the product.",
    )
    l10n_ke_product_type_code = fields.Selection(
        string="eTIMS Product Type",
        selection=PRODUCT_TYPE_CODE_SELECTION,
        compute='_compute_l10n_ke_product_type_code',
        store=True,
        readonly=False,
        help="Used by eTIMS to determine the type of the product",
    )
    l10n_ke_is_insurance_applicable = fields.Boolean(
        string="Insurance Applicable",
        help="Check this box if the product is covered by insurance.",
    )
    l10n_ke_item_code = fields.Char(
        string="Item Code",
        help="The code assigned to this product on eTIMS",
        readonly=True,
    )

    # === Computes / Getters === #

    @api.depends('type')
    def _compute_l10n_ke_packaging_unit_id(self):
        service_packaging = self.env.ref('l10n_ke_edi_oscu.code_17_OU', raise_if_not_found=False)
        for product in self.filtered(lambda p: not p.l10n_ke_packaging_unit_id):
            product.l10n_ke_packaging_unit_id = service_packaging if product.type == 'service' else None

    @api.depends('type')
    def _compute_l10n_ke_product_type_code(self):
        for product in self:
            if product.type == 'service':
                product.l10n_ke_product_type_code = '3'

    def _l10n_ke_get_validation_messages(self, for_invoice=False):
        """ Validate the product configuration and generate warning messages.

        :param bool for_invoice: whether the validations should be done for the purpose of sending
            the product information in an invoice, or for the purpose of saving the product.
        :returns: a dictionary, containing the message, an associated action and a name
            for the action.
        """
        messages = {}

        products_missing_fields = self.filtered(
            lambda p: (
                not p.unspsc_code_id or not p.l10n_ke_packaging_unit_id
                or not p.l10n_ke_packaging_quantity
                or (
                    not for_invoice
                    and (
                        not p.standard_price
                        or not p.l10n_ke_origin_country_id
                        or not p.l10n_ke_product_type_code
                    )
                )
                or not p.taxes_id
            )
        )

        if products_missing_fields:
            if for_invoice:
                message = _(
                    "When sending to eTIMS, the products used must have a defined Packaging Unit, "
                    "Packaging Quantity, Sales Taxes and UNSPSC Code."
                )
            else:
                message = _(
                    "When sending to eTIMS, the products used must have a defined Cost, Product Type, "
                    "Origin Country, Packaging Unit, Packaging Quantity, Sales Taxes and UNSPSC Code."
                )

            messages['product_fields_missing'] = {
                'message': message,
                'action_text': _("View Product(s)"),
                'action': products_missing_fields._l10n_ke_action_open_products(),
                'blocking': True,
            }

        products_incorrect_taxes = self.filtered(
            lambda p: len(p.taxes_id.filtered(lambda t: t.l10n_ke_tax_type_id and t.company_id in self.env.company.parent_ids)) > 1
        )
        if products_incorrect_taxes:
            messages['product_incorrect_taxes'] = {
                'message': _("Only one tax with a KRA tax code should be set on the product!"),
                'action_text': _("View Product(s)"),
                'action': products_incorrect_taxes._get_records_action(name=_("View Product(s)"), context={}),
            }

        products_mismatched_taxes = self.filtered(
            lambda p: p.taxes_id.filtered(
                lambda t: (
                    t.l10n_ke_tax_type_id
                    and t.company_id in self.env.company.parent_ids
                    and p.unspsc_code_id.l10n_ke_tax_type_id
                    and t.l10n_ke_tax_type_id != p.unspsc_code_id.l10n_ke_tax_type_id
                )
            )
        )
        if products_mismatched_taxes:
            messages['product_mismatched_taxes'] = {
                'message': _(
                    "The tax set on the product has tax code %(product_tax_code)s, which differs from "
                    "the tax code %(unspsc_tax_code)s specified by the KRA for the UNSPSC code.",
                    product_tax_code=products_mismatched_taxes[0].taxes_id.filtered(lambda t: t.company_id in self.env.company.parent_ids).l10n_ke_tax_type_id.code,
                    unspsc_tax_code=products_mismatched_taxes[0].unspsc_code_id.l10n_ke_tax_type_id.code,
                ),
                'action_text': _("View Product(s)"),
                'action': products_incorrect_taxes._get_records_action(name=_("View Product(s)"), context={}),
            }

        return messages

    def _l10n_ke_get_tax_type(self):
        """ Get the tax type associated with the product, given the current company. """
        self.ensure_one()
        return self.taxes_id.filtered(lambda t: t.company_id in self.env.company.parent_ids).l10n_ke_tax_type_id

    def _l10n_ke_action_open_products(self, title=None):
        """ Open a view with the required fields for saving a product on eTIMS """
        res = {
            'name': title or _("Products"),
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'domain': [('id', 'in', self.ids)],
            'views': [(self.env.ref('l10n_ke_edi_oscu.l10n_ke_kra_product_tree').id, 'list'), (False, 'form')],
            'context': {'create': False, 'delete': False},
        }
        return res

    # === Saving to KRA === #

    def _calculate_l10n_ke_item_code(self):
        """ Computes the item code of a given product

        For instance KE1NTXU is an item code, where
        KE:      first two digits are the origin country of the product
        1:       the product type (raw material)
        NT:      the packaging type
        XU:      the quantity type
        0000006: a unique value (id in our case)
        """
        code_fields = [
            self.l10n_ke_origin_country_id.code,
            self.l10n_ke_product_type_code,
            self.l10n_ke_packaging_unit_id.code,
            self.uom_id.l10n_ke_quantity_unit_id.code,
        ]
        if not all(code_fields):
            return None

        item_code_prefix = ''.join(code_fields)
        return item_code_prefix.ljust(20 - len(str(self.id)), '0') + str(self.id)

    def _l10n_ke_oscu_save_item_content(self):
        """ Get a dict of values to be sent to the KRA for saving a product's information. """
        self.ensure_one()
        code = self.l10n_ke_item_code or self._calculate_l10n_ke_item_code()
        content = {
            'itemCd':      code,                                                  # Item Code
            'itemClsCd':   self.unspsc_code_id.code or '',                        # HS Code (unspsc format)
            'itemTyCd':    self.l10n_ke_product_type_code,                        # Generally raw material, finished product, service
            'itemNm':      self.name,                                             # Product name
            'orgnNatCd':   self.l10n_ke_origin_country_id.code,                   # Origin nation code
            'pkgUnitCd':   self.l10n_ke_packaging_unit_id.code,                   # Packaging unit code
            'qtyUnitCd':   self.uom_id.l10n_ke_quantity_unit_id.code,             # Quantity unit code
            'taxTyCd':     self._l10n_ke_get_tax_type().code,                     # Tax type code
            'bcd':         self.barcode or None,                                  # Self barcode
            'dftPrc':      json_float_round(self.standard_price, 2),              # Standard price
            'isrcAplcbYn': 'Y' if self.l10n_ke_is_insurance_applicable else 'N',  # Is insurance applicable
            'useYn': 'Y',
            **self.env.company._l10n_ke_get_user_dict(self.create_uid, self.write_uid),
        }
        return content

    def _l10n_ke_oscu_save_item(self, company=None):
        """ Register a product with eTIMS. """
        company = company or self.env.company
        content = self._l10n_ke_oscu_save_item_content()
        error, _data, _date = company._l10n_ke_call_etims('saveItem', content)
        if not error:
            self.l10n_ke_item_code = content['itemCd']
        return error, content

    def action_l10n_ke_oscu_save_item(self):
        """ Register a product with eTIMS (user action).

        Regstration allows the product to be used via its itemCd in other requests such as invoice
        and stock move reporting.
        """
        validation_messages = self._l10n_ke_get_validation_messages(for_invoice=False)
        validation_messages.update(self.uom_id._l10n_ke_get_validation_messages())
        for message in validation_messages.values():
            if message.get('blocking'):
                raise UserError(_("Cannot register '%(name)s' on eTIMS:\n%(msg)s", name=self.name, msg=message['message']))
        error, _content = self._l10n_ke_oscu_save_item()
        if error:
            raise UserError(f"[{error['code']}] {error['message']}")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'sticky': False,
                'message': _("Product successfully registered"),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    # === Helpers for invoice import === #

    @api.model
    def _l10n_ke_oscu_find_product_from_json(self, product_dict):
        """ Find a product matching that of a given product represented json format provided by the API

        :param dict product_dict: dictionary representing the fields of the product as obtained from
                                  the API.
        :returns:                 a tuple, containing a product (or None type) that is strongest
                                  match to an item with the given details, and a message
                                  describing the method by which the matching that was accomplished.
        """
        if product_dict.get('bcd'):
            search_domain = [('barcode', '=', product_dict['bcd']), ('unspsc_code_id.code', '=', product_dict['itemClsCd'])]
            if (product := self.search(search_domain, limit=1)):
                return product, _('"%s" matched using an exact matching of barcode and UNSPSC code.', product.name)
            else:
                return None, _(
                    '"%(item_name)s" could not be matched to any product, since it has a barcode (%(barcode)s) and UNSPSC'
                    'code (%(unspsc_code)s) that do not match any existing product.',
                    item_name=product_dict['itemNm'],
                    barcode=product_dict['bcd'],
                    unspsc_code=product_dict['itemClsCd'],
                )

        if (product := self.search([
            ('unspsc_code_id.code', '=', product_dict['itemClsCd']),
            ('name', 'ilike', product_dict['itemNm'])
        ], limit=1)):
            return product, _('"%s" matched using an exact matching of name and UNSPSC code.', product.name)

        fuzzy_name = ('name', 'ilike', f"%{'%'.join(product_dict['itemNm'].split())}%")
        search_domain = [('unspsc_code_id.code', '=', product_dict['itemClsCd']), fuzzy_name]
        if (product := product_dict.get('itemClsCd') and self.search(search_domain, limit=1)):
            return product, _(
                '"%s" matched using an inexact matching of name and an exact matching of UNSPSC code.',
                product.name
            )

        return None, _(
            'The product "%(product_name)s" with UNSPSC code: "%(unspsc_code)s" could not be matched to any existing product.',
            product_name=product_dict['itemNm'],
            unspsc_code=product_dict['itemClsCd'],
        )


class ProductCode(models.Model):
    _inherit = 'product.unspsc.code'

    l10n_ke_tax_type_id = fields.Many2one('l10n_ke_edi_oscu.code')

    def _cron_l10n_ke_oscu_get_codes_from_device(self):
        """ Automatically fetch and create UNSPSC codes from the OSCU if they don't already exist """
        company = self.env['res.company']._l10n_ke_find_for_cron(failed_action='No KRA Codes fetched.')
        if not company:
            return

        tax_codes = {
            tax_code['code']: tax_code['id']
            for tax_code in self.env['l10n_ke_edi_oscu.code'].search_read([('code_type', '=', '04')], ['code'])
        }
        last_request_date = self.env['ir.config_parameter'].get_param('l10n_ke_oscu.last_unspsc_code_request_date', '20180101000000')
        error, data, _date = company._l10n_ke_call_etims('selectItemClsList', {'lastReqDt': last_request_date})
        if error:
            if error.get('code') == '001':
                _logger.info("No new UNSPSC codes fetched from the OSCU.")
                return
            raise UserError(f"[{error['code']}] {error['message']}")

        cls_list = {item['itemClsCd']: item for item in data['itemClsList']}
        existing_codes = self.with_context(active_test=False).search([
            ('code', 'in', list(cls_list.keys()))
        ])
        for code in existing_codes:
            if (new_tax_code := not code.l10n_ke_tax_type_id and cls_list[code.code]['taxTyCd']):
                code.write({'l10n_ke_tax_type_id': tax_codes.get(new_tax_code)})

        new_codes = self.env['product.unspsc.code'].create([
            {
                'name': code_dict['itemClsNm'],
                'code': code,
                'applies_to': 'product',
                'l10n_ke_tax_type_id': tax_codes.get(code_dict['taxTyCd']),
                'active': True,
            }
            for code, code_dict in cls_list.items() if code not in existing_codes.mapped('code')
        ])
        if new_codes:
            self._cr.execute(SQL("""
                INSERT INTO ir_model_data
                (name, res_id, module, model, noupdate)
                SELECT concat('unspsc_code_', code), id, 'product_unspsc', 'product.unspsc.code', 't'
                FROM product_unspsc_code
                WHERE product_unspsc_code.id IN %s""", tuple(new_codes.ids)))

        _logger.info("%i UNSPSC codes fetched from the OSCU, %i UNSPSC codes created", len(cls_list), len(new_codes))
        self.env['ir.config_parameter'].sudo().set_param('l10n_ke_oscu.last_unspsc_code_request_date', format_etims_datetime(fields.Datetime.now()))
