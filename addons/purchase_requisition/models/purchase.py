# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, get_lang


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    requisition_id = fields.Many2one('purchase.requisition', string='Agreement', copy=False, index='btree_not_null')
    requisition_type = fields.Selection(related='requisition_id.requisition_type')

    @api.onchange('requisition_id')
    def _onchange_requisition_id(self):
        if not self.requisition_id:
            return

        self = self.with_company(self.company_id)
        requisition = self.requisition_id
        if self.partner_id:
            partner = self.partner_id
        else:
            partner = requisition.vendor_id
        payment_term = partner.property_supplier_payment_term_id

        FiscalPosition = self.env['account.fiscal.position']
        fpos = FiscalPosition.with_company(self.company_id)._get_fiscal_position(partner)

        self.partner_id = partner.id
        self.fiscal_position_id = fpos.id
        self.payment_term_id = payment_term.id
        self.company_id = requisition.company_id.id
        self.currency_id = requisition.currency_id.id
        if not self.origin or requisition.name not in self.origin.split(', '):
            if self.origin:
                if requisition.name:
                    self.origin = self.origin + ', ' + requisition.name
            else:
                self.origin = requisition.name
        self.note = requisition.description
        if requisition.date_start:
            self.date_order = max(fields.Datetime.now(), fields.Datetime.to_datetime(requisition.date_start))
        else:
            self.date_order = fields.Datetime.now()

        # Create PO lines if necessary
        # Do not clobber existing lines if the PO is already confirmed
        if self.state != 'draft':
            return
        order_lines = []
        for line in requisition.line_ids:
            # Compute name
            product_lang = line.product_id.with_context(
                lang=partner.lang or self.env.user.lang,
                partner_id=partner.id
            )
            name = product_lang.display_name
            if product_lang.description_purchase:
                name += '\n' + product_lang.description_purchase

            # Compute taxes
            taxes_ids = fpos.map_tax(line.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id in requisition.company_id.parent_ids)).ids

            product_qty = line.product_qty if requisition.requisition_type == 'purchase_template' else 0
            # Create PO line
            order_line_values = line._prepare_purchase_order_line(
                name=name, product_qty=product_qty, price_unit=line.price_unit,
                taxes_ids=taxes_ids)
            order_lines.append((0, 0, order_line_values))
        self.order_line = order_lines

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            if order.requisition_id:
                order.message_post_with_source(
                    'mail.message_origin_link',
                    render_values={'self': order, 'origin': order.requisition_id},
                    subtype_xmlid='mail.mt_note',
                )
        return orders

    def write(self, vals):
        result = super(PurchaseOrder, self).write(vals)
        if vals.get('requisition_id'):
            for order in self:
                order.message_post_with_source(
                    'mail.message_origin_link',
                    render_values={'self': order, 'origin': order.requisition_id, 'edit': True},
                    subtype_xmlid='mail.mt_note',
                )
        return result

    def _prepare_grouped_data(self, rfq):
        match_fields = super()._prepare_grouped_data(rfq)
        return match_fields + (rfq.requisition_id.id,)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _compute_price_unit_and_date_planned_and_name(self):
        po_lines_without_requisition = self.env['purchase.order.line']
        for pol in self:
            if pol.product_id.id not in pol.order_id.requisition_id.line_ids.product_id.ids:
                po_lines_without_requisition |= pol
                continue

            line = None
            # Match the requisition line with exact UoM first, then product-only as fallback.
            for req_line in pol.order_id.requisition_id.line_ids:
                if req_line.product_id == pol.product_id:
                    line = req_line
                    if req_line.product_uom_id == pol.product_uom_id:
                        break

            pol.price_unit = line.product_uom_id._compute_price(line.price_unit, pol.product_uom_id)
            partner = pol.order_id.partner_id or pol.order_id.requisition_id.vendor_id
            params = {'order_id': pol.order_id}
            seller = pol.product_id._select_seller(
                partner_id=partner,
                quantity=pol.product_qty,
                date=pol.order_id.date_order and pol.order_id.date_order.date(),
                uom_id=line.product_uom_id,
                params=params)
            if not pol.date_planned:
                pol.date_planned = pol._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            product_ctx = {'seller_id': seller.id, 'lang': get_lang(pol.env, partner.lang).code}
            name = pol._get_product_purchase_description(pol.product_id.with_context(product_ctx))
            if line.product_description_variants:
                name += '\n' + line.product_description_variants
            pol.name = name
        super(PurchaseOrderLine, po_lines_without_requisition)._compute_price_unit_and_date_planned_and_name()
