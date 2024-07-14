# -*- coding: utf-8 -*-

import datetime

from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_round, ormcache

from .taxcloud_request import TaxCloudRequest


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Used to determine whether or not to warn the user to configure TaxCloud
    is_taxcloud_configured = fields.Boolean(related='company_id.is_taxcloud_configured')
    # Technical field to determine whether to hide taxes in views or not
    is_taxcloud = fields.Boolean(related='fiscal_position_id.is_taxcloud')

    def action_quotation_send(self):
        self.validate_taxes_on_sales_order()
        return super().action_quotation_send()

    def action_quotation_sent(self):
        for order in self:
            order.validate_taxes_on_sales_order()
        return super().action_quotation_sent()

    @api.model
    def _get_TaxCloudRequest(self, api_id, api_key):
        return TaxCloudRequest(api_id, api_key)

    @api.model
    @ormcache('request_hash')
    def _get_all_taxes_values(self, request, request_hash):
        return request.get_all_taxes_values()

    def validate_taxes_on_sales_order(self):
        if not self.fiscal_position_id.is_taxcloud:
            return True
        company = self.company_id
        shipper = company or self.env.company
        api_id = shipper.taxcloud_api_id
        api_key = shipper.taxcloud_api_key
        request = self._get_TaxCloudRequest(api_id, api_key)

        request.set_location_origin_detail(shipper)
        request.set_location_destination_detail(self.partner_shipping_id)

        request.set_order_items_detail(self)
        request.taxcloud_date = fields.Datetime.context_timestamp(self, datetime.datetime.now())

        response = self._get_all_taxes_values(request, request.hash)

        if response.get('error_message'):
            raise ValidationError(
                _('Unable to retrieve taxes from TaxCloud: ') + '\n' +
                response['error_message']
            )

        tax_values = response['values']

        # warning: this is tightly coupled to TaxCloudRequest's _process_lines method
        # do not modify without syncing the other method
        for index, line in enumerate(self.order_line.filtered(lambda l: not l.display_type)):
            if line._get_taxcloud_price() >= 0.0 and line.product_uom_qty >= 0.0:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0) * line.product_uom_qty
                if not price:
                    tax_rate = 0.0
                else:
                    tax_rate = tax_values[index] / price * 100
                if len(line.tax_id) != 1 or float_compare(line.tax_id.amount, tax_rate, precision_digits=3):
                    tax_rate = float_round(tax_rate, precision_digits=3)
                    tax = self.env['account.tax'].with_context(active_test=False).sudo().search([
                        *self.env['account.tax']._check_company_domain(company),
                        ('amount', '=', tax_rate),
                        ('amount_type', '=', 'percent'),
                        ('type_tax_use', '=', 'sale'),
                    ], limit=1)
                    if tax:
                        # Only set if not already set, otherwise it triggers a
                        # needless and potentially heavy recompute for
                        # everything related to the tax.
                        if not tax.active:
                            tax.active = True  # Needs to be active to be included in order total computation
                    else:
                        tax = self.env['account.tax'].sudo().with_context(default_company_id=company.id).create({
                            'name': 'Tax %.3f %%' % (tax_rate),
                            'amount': tax_rate,
                            'amount_type': 'percent',
                            'type_tax_use': 'sale',
                            'description': 'Sales Tax',
                        })
                    line.tax_id = tax
        return True

    def add_option_to_order_with_taxcloud(self):
        self.ensure_one()
        # portal user call this method with sudo
        if self.fiscal_position_id.is_taxcloud and self._uid == SUPERUSER_ID:
            self.validate_taxes_on_sales_order()


class SaleOrderLine(models.Model):
    """Defines getters to have a common facade for order and invoice lines in TaxCloud."""
    _inherit = 'sale.order.line'

    def _get_taxcloud_price(self):
        self.ensure_one()
        return self.price_unit

    def _get_qty(self):
        self.ensure_one()
        return self.product_uom_qty
