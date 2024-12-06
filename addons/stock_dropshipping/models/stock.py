# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.osv import expression


class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.model
    def _get_procurements_to_merge_groupby(self, procurement):
        """ Do not group purchase order line if they are linked to different
        sale order line. The purpose is to compute the delivered quantities.
        """
        return procurement.values.get('sale_line_id'), super(StockRule, self)._get_procurements_to_merge_groupby(procurement)

    def _get_partner_id(self, values, rule):
        route = self.env.ref('stock_dropshipping.route_drop_shipping', raise_if_not_found=False)
        if route and rule.route_id == route:
            return False
        return super()._get_partner_id(values, rule)


class ProcurementGroup(models.Model):
    _inherit = "procurement.group"

    @api.model
    def _get_rule_domain(self, location, values):
        domain = super()._get_rule_domain(location, values)
        if 'sale_line_id' in values and values.get('company_id'):
            domain = expression.AND([domain, [('company_id', '=', values['company_id'].id)]])
        return domain


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_dropship = fields.Boolean("Is a Dropship", compute='_compute_is_dropship')

    @api.depends('location_dest_id.usage', 'location_dest_id.company_id', 'location_id.usage', 'location_id.company_id')
    def _compute_is_dropship(self):
        for picking in self:
            source, dest = picking.location_id, picking.location_dest_id
            picking.is_dropship = (source.usage == 'supplier' or (source.usage == 'transit' and not source.company_id)) \
                              and (dest.usage == 'customer' or (dest.usage == 'transit' and not dest.company_id))

    def _is_to_external_location(self):
        self.ensure_one()
        return super()._is_to_external_location() or self.is_dropship

    def _send_confirmation_email(self):
        subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')
        for stock_pick in self.filtered(lambda p: p.company_id.stock_move_email_validation and p.picking_type_id.code == 'dropship'):
            delivery_template = stock_pick.company_id.stock_mail_confirmation_template_id
            if stock_pick.purchase_id.dest_address_id:
                dropshipping_template = self.env.ref('stock_dropshipping.mail_template_data_delivery_confirmation_dropship', raise_if_not_found=False)
                delivery_template = dropshipping_template or delivery_template
            stock_pick.with_context(force_send=True).message_post_with_source(
                delivery_template,
                email_layout_xmlid='mail.mail_notification_light',
                subtype_id=subtype_id,
            )
        super()._send_confirmation_email()

    def _get_report_base_filename(self):
        picking_report_name = super()._get_report_base_filename()
        if self.picking_type_code == 'dropship' and self.purchase_id.dest_address_id:
            picking_report_name = _("Delivery Slip - %s", f"{self.purchase_id.dest_address_id.name} - {self.name}")
        return picking_report_name


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    code = fields.Selection(
        selection_add=[('dropship', 'Dropship')], ondelete={'dropship': lambda recs: recs.write({'code': 'outgoing', 'active': False})})

    def _compute_default_location_src_id(self):
        dropship_types = self.filtered(lambda pt: pt.code == 'dropship')
        dropship_types.default_location_src_id = self.env.ref('stock.stock_location_suppliers').id

        super(StockPickingType, self - dropship_types)._compute_default_location_src_id()

    def _compute_default_location_dest_id(self):
        dropship_types = self.filtered(lambda pt: pt.code == 'dropship')
        dropship_types.default_location_dest_id = self.env.ref('stock.stock_location_customers').id

        super(StockPickingType, self - dropship_types)._compute_default_location_dest_id()

    @api.depends('default_location_src_id', 'default_location_dest_id')
    def _compute_warehouse_id(self):
        super()._compute_warehouse_id()
        for picking_type in self:
            if picking_type.default_location_src_id.usage == 'supplier' and picking_type.default_location_dest_id.usage == 'customer':
                picking_type.warehouse_id = False

    @api.depends('code')
    def _compute_show_picking_type(self):
        super()._compute_show_picking_type()
        for record in self:
            if record.code == "dropship":
                record.show_picking_type = True


class StockLot(models.Model):
    _inherit = 'stock.lot'

    def _compute_last_delivery_partner_id(self):
        super()._compute_last_delivery_partner_id()
        for lot in self:
            if lot.delivery_count > 0:
                last_delivery = max(lot.delivery_ids, key=lambda d: d.date_done)
                if last_delivery.is_dropship:
                    lot.last_delivery_partner_id = last_delivery.sale_id.partner_id

    def _get_outgoing_domain(self):
        res = super()._get_outgoing_domain()
        return expression.OR([res, [
            ('location_dest_id.usage', '=', 'customer'),
            ('location_id.usage', '=', 'supplier'),
        ]])
