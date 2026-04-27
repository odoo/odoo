from odoo import _, api, models
from odoo.exceptions import ValidationError


class PosOrder(models.Model):
    _name = 'pos.order'
    _inherit = ['pos.order', 'account.external.tax.mixin', 'account.avatax.unique.code']

    # Main mixin overrides
    def _get_date_for_external_taxes(self):
        return self.date_order

    def _get_and_set_external_taxes_on_eligible_records(self):
        """ account.external.tax.mixin override. """
        eligible_orders = self.filtered(lambda order: order.is_tax_computed_externally and order.state in ('draft'))
        eligible_orders._set_external_taxes(*eligible_orders._get_external_taxes())
        return super()._get_and_set_external_taxes_on_eligible_records()

    def _get_lines_eligible_for_external_taxes(self):
        """ account.external.tax.mixin override. """
        return self.lines

    def _get_line_data_for_external_taxes(self):
        """ account.external.tax.mixin override. """
        res = []
        for line in self._get_lines_eligible_for_external_taxes():
            # Clear all taxes (e.g. default customer tax). Not every line will be sent to the external tax
            # calculation service, those lines would keep their default taxes otherwise.
            line.tax_ids = False
            pos_config = line.order_id.config_id
            res.append({
                "id": line.id,
                "model_name": line._name,
                "product_id": line.product_id,
                "qty": line.qty,
                "price_subtotal": line.price_subtotal,
                "price_unit": line.price_unit,
                "discount": line.discount,
                "is_refund": False,
                "warehouse_id": pos_config.warehouse_id if pos_config.ship_later else False
            })
        return res

    def _set_external_taxes(self, mapped_taxes, summary):
        """ account.external.tax.mixin override. """
        to_flush = self.env['pos.order.line']
        for line, detail in mapped_taxes.items():
            line.tax_ids = detail['tax_ids']
            to_flush += line

        # Trigger field computation due to changing the tax id. Do
        # this here because we will manually change the taxes.
        to_flush.flush_recordset(['price_subtotal', 'price_subtotal_incl'])

        for line, detail in mapped_taxes.items():
            line.price_subtotal = detail['total']
            line.price_subtotal_incl = detail['tax_amount'] + detail['total']

        for order in self:
            order.amount_tax = sum(line.price_subtotal_incl - line.price_subtotal for line in order.lines)
            order.amount_total = sum(line.price_subtotal_incl for line in order.lines)

    def _get_avatax_dates(self):
        """ account.external.tax.mixin override. """
        return self._get_date_for_external_taxes(), self._get_date_for_external_taxes()

    def _get_avatax_ship_to_partner(self):
        """ account.external.tax.mixin override. """
        return self.partner_id

    def _get_avatax_document_type(self):
        """ account.external.tax.mixin override. """
        return 'SalesOrder'

    def _get_avatax_description(self):
        """ account.external.tax.mixin override. """
        return 'PoS Order'

    def _get_invoice_grouping_keys(self):
        res = super()._get_invoice_grouping_keys()
        if self.filtered('fiscal_position_id.is_avatax'):
            res += ['partner_id']
        return res

    def _get_avatax_address_from_partner(self, partner):
        if partner:
            return super()._get_avatax_address_from_partner(partner)
        raise ValidationError(_('Avatax requires your current location or a customer to be set on the order with a proper zip, state and country.'))

    @api.model
    def get_order_tax_details(self, orders):
        res = self.env['pos.order'].sync_from_ui(orders)
        order_ids = self.browse([order['id'] for order in res['pos.order']])
        results = {
            'pos.order': [],
            'pos.order.line': [],
            'account.tax': [],
            'account.tax.group': [],
        }

        for order in order_ids:
            order.button_external_tax_calculation()
            config_id = order.config_id
            results['account.tax'] += order.lines.tax_ids.read(self.env['account.tax']._load_pos_data_fields(config_id), load=False)
            results['account.tax.group'] += order.lines.tax_ids.tax_group_id.read(self.env['account.tax.group']._load_pos_data_fields(config_id), load=False)
            results['pos.order'] += order.read(order._load_pos_data_fields(config_id), load=False)
            results['pos.order.line'] += order.lines.read(order.lines._load_pos_data_fields(config_id), load=False) if config_id else []

        return results
