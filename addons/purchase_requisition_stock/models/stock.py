# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_purchase_order(self, company_id, origins, values):
        res = super(StockRule, self)._prepare_purchase_order(company_id, origins, values)
        values = values[0]
        requisition = self._get_supplier_requisition(values)
        res['partner_ref'] = requisition.name
        res['requisition_id'] = requisition
        if requisition.currency_id:
            res['currency_id'] = requisition.currency_id.id
        return res

    def _make_po_get_domain(self, company_id, values, partner):
        domain = super(StockRule, self)._make_po_get_domain(company_id, values, partner)
        requisition = self._get_supplier_requisition(values)
        if requisition:
            domain += (
                ('requisition_id', '=', requisition.id),
            )
        return domain

    def _get_supplier_requisition(self, values):
        # the seller information only holds a pricelist when it does not come from the purchase history
        seller_info = values.get('supplier') or {}
        return seller_info.get('supplierinfo', self.env['product.supplierinfo']).purchase_requisition_id

    def _pick_supplier(self, company, product, partner=False, qty=None, uom=False, date=None, params=False):
        p = product.with_company(company)
        all_sellers = p._get_filtered_sellers(partner_id=partner, quantity=None, date=None, uom_id=uom, params=params)
        agreement_sellers = all_sellers.filtered(lambda s: s.purchase_requisition_id)
        for agreement_seller in agreement_sellers:
            if agreement_seller.purchase_requisition_line_id.remaining_qty < qty:
                continue
            if agreement_seller.min_qty > qty:
                continue
            if not date:
                return agreement_seller._get_seller_info()
            start_date = agreement_seller.purchase_requisition_id.date_start
            end_date = agreement_seller.purchase_requisition_id.date_end
            if (not start_date or date >= start_date) and (not end_date or date <= end_date):
                return agreement_seller._get_seller_info()
        return super()._pick_supplier(company, product, partner=partner, qty=qty, uom=uom, date=date, params=params)

class StockMove(models.Model):
    _inherit = 'stock.move'

    requisition_line_ids = fields.One2many('purchase.requisition.line', 'move_dest_id')

    def _get_upstream_documents_and_responsibles(self, visited):
        # People without purchase rights should be able to do this operation
        requisition_lines_sudo = self.sudo().requisition_line_ids
        if requisition_lines_sudo:
            return [(requisition_line.requisition_id, requisition_line.requisition_id.user_id, visited) for requisition_line in requisition_lines_sudo if requisition_line.requisition_id.state not in ('done', 'cancel')]
        else:
            return super(StockMove, self)._get_upstream_documents_and_responsibles(visited)
