# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, models, _
from odoo.exceptions import UserError


class purchase_order(models.Model):
    _inherit = "purchase.order"

    def _prepare_sale_order_data(self, name, partner, company, direct_delivery_address):
        res = super()._prepare_sale_order_data(name, partner, company, direct_delivery_address)
        warehouse = company.intercompany_warehouse_id and company.intercompany_warehouse_id.company_id.id == company.id and company.intercompany_warehouse_id or False
        if not warehouse:
            raise UserError(_('Configure correct warehouse for company(%s) from Menu: Settings/Users/Companies', company.name))
        res['warehouse_id'] = warehouse.id

        picking_type_warehouse_partner_id = self.picking_type_id.warehouse_id.partner_id.id
        if picking_type_warehouse_partner_id:
            res['partner_shipping_id'] = picking_type_warehouse_partner_id or direct_delivery_address

        return res

    def _prepare_sale_order_line_data(self, line, company):
        res = super()._prepare_sale_order_line_data(line, company)
        if line.product_id.sale_delay:
            res['customer_lead'] = line.product_id and line.product_id.sale_delay or 0.0
        # adds a product_custom_attribute_value_ids if the PO was generated from an SO
        so_lines = self.env['stock.move'].browse(line.move_ids._rollup_move_dests()).mapped('sale_line_id')
        so_line = so_lines[0] if so_lines else line.move_dest_ids.sale_line_id
        pcavs = so_line.product_custom_attribute_value_ids
        pcavs_vals_list = []
        for pcav in pcavs:
            pcavs_vals_list.append(Command.create({
                'custom_product_template_attribute_value_id': pcav.custom_product_template_attribute_value_id.id,
                'custom_value': pcav.custom_value,
            }))
        res['product_custom_attribute_value_ids'] = pcavs_vals_list
        return res

    def _get_destination_location(self):
        self.ensure_one()
        res = super()._get_destination_location()

        if self.dest_address_id and self.sale_order_count:
            sale_order = self._get_sale_orders()[0]
            partner_company = self.env['res.company']._find_company_from_partner(sale_order.partner_id.id)
            if partner_company and partner_company != self.company_id and self.dest_address_id != sale_order.partner_id:
                # Means that's we're in inter-company transaction -> Must dropship to inter-company transit.
                return sale_order.partner_id.property_stock_customer.id
        return res
