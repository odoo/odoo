# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, get_lang


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    requisition_ids = fields.Many2many(
        'purchase.requisition',
        relation='purchase_order_requisition_rel',
        string='Agreements',
        compute='_compute_requisition_ids', store=True, readonly=False,
    )
    requisition_type = fields.Selection(related='requisition_ids.requisition_type')
    date_order_warning = fields.Char(compute='_compute_date_order_warning')

    @api.depends('order_line.requisition_line_id.requisition_id')
    def _compute_requisition_ids(self):
        for order in self:
            order.requisition_ids = order.order_line.requisition_line_id.requisition_id

    @api.depends('date_order', 'requisition_ids.date_start', 'requisition_ids.date_end')
    def _compute_date_order_warning(self):
        for order in self:
            if not order.date_order:
                order.date_order_warning = False
                continue
            order_date = fields.Date.context_today(order, order.date_order)
            violating_requisitions = order.requisition_ids.filtered(
                lambda r: (r.date_start and order_date < r.date_start) or
                            (r.date_end and order_date > r.date_end)
            ).mapped('name')
            if not violating_requisitions:
                order.date_order_warning = False
            else:
                order.date_order_warning = _("You are placing an order outside the %s validity period", ", ".join(violating_requisitions))

    @api.onchange('requisition_ids')
    def _onchange_requisition_ids(self):

        self = self.with_company(self.company_id)
        requisition = self.requisition_ids

        # remove lines belonging to deselected requisitions
        selected_reqs = requisition._origin
        lines_to_remove = self.order_line.filtered(
            lambda l: l.requisition_line_id._origin
            and l.requisition_line_id._origin.requisition_id not in selected_reqs
        )
        self.order_line -= lines_to_remove

        if not selected_reqs:
            return

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

        # setting origin
        existing_origins = self.origin.split(', ') if self.origin else []
        req_names = requisition.mapped('name')
        all_origins = []
        for name in existing_origins + req_names:
            if name and name not in all_origins:
                all_origins.append(name)
        self.origin = ', '.join(all_origins)

        # setting description
        self.note = '\n\n'.join(d for d in requisition.mapped('description') if d)

        # getting the max date of the requisition start dates and now
        start_dates = requisition.filtered('date_start').mapped(
            lambda r: fields.Datetime.to_datetime(r.date_start),
        )
        self.date_order = max(start_dates + [fields.Datetime.now()])

        # Create/remove PO lines if necessary
        if self.state != 'draft':
            return
        order_lines = []
        existing_req_lines = self.order_line.requisition_line_id._origin
        for req in requisition:
            for line in req.line_ids:
                # skip lines already added
                if line._origin in existing_req_lines:
                    continue
                if line.display_type:
                    order_lines.append((0, 0, line._prepare_purchase_order_line(name=False)))
                    continue
                # Compute name
                product_lang = line.product_id.with_context(
                    lang=partner.lang or self.env.user.lang,
                    partner_id=partner.id
                )
                name = product_lang.display_name
                if product_lang.description_purchase:
                    name += '\n' + product_lang.description_purchase

                # Compute taxes
                taxes_ids = fpos.map_tax(line.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id in req.company_id.parent_ids)).ids

                product_qty = line.product_qty if req.requisition_type == 'purchase_template' else 0
                # Create PO line
                order_line_values = line._prepare_purchase_order_line(
                    name=name, product_qty=product_qty, price_unit=line.price_unit,
                    taxes_ids=taxes_ids)
                order_lines.append((0, 0, order_line_values))
        self.order_line = order_lines

    @api.onchange('date_planned')
    def onchange_date_planned(self):
        dates = self.order_line.filtered(lambda l: not l.display_type and l.date_planned).mapped('date_planned')
        if dates and self.date_planned == min(dates):
            return
        super().onchange_date_planned()

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            if order.requisition_ids:
                order.message_post_with_source(
                    'mail.message_origin_link',
                    render_values={'self': order, 'origin': order.requisition_ids},
                    subtype_xmlid='mail.mt_note',
                )
        return orders

    def write(self, vals):
        result = super(PurchaseOrder, self).write(vals)
        if vals.get('requisition_ids'):
            for order in self:
                order.message_post_with_source(
                    'mail.message_origin_link',
                    render_values={'self': order, 'origin': order.requisition_ids, 'edit': True},
                    subtype_xmlid='mail.mt_note',
                )
        return result

    def _prepare_grouped_data(self, rfq):
        match_fields = super()._prepare_grouped_data(rfq)
        return match_fields + (tuple(rfq.requisition_ids.ids),)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    requisition_line_id = fields.Many2one(
        'purchase.requisition.line',
        compute='_compute_requisition_line_id', store=True, readonly=False,
        ondelete='set null',
        index=True,
    )
    order_too_big_warning = fields.Char(compute='_compute_order_too_big_warning')

    @api.depends('product_id')
    def _compute_requisition_line_id(self):
        for line in self:
            if line.requisition_line_id.product_id == line.product_id:
                continue
            line.requisition_line_id = line.order_id.requisition_ids.line_ids.filtered(
                lambda l: l.product_id and l.product_id == line.product_id and l.remaining_qty > 0)[:1]

    @api.depends('product_qty', 'uom_id', 'order_id.state',
                 'requisition_line_id.remaining_qty', 'requisition_line_id.uom_id')
    def _compute_order_too_big_warning(self):
        for line in self:
            line.order_too_big_warning = False
            req_line = line.requisition_line_id
            if not req_line or not line.uom_id:
                continue

            if line.order_id.state == 'purchase':
                is_exceeded = req_line.remaining_qty < 0
            else:
                qty = line.uom_id._compute_quantity(line.product_qty, req_line.uom_id, round=False)
                is_exceeded = qty > req_line.remaining_qty
            if is_exceeded:
                line.order_too_big_warning = _(
                    "Ordering this quantity will make the total ordered quantity for %s exceed the agreed-upon quantity",
                    req_line.requisition_id.display_name,
                )

    @api.depends('requisition_line_id')
    def _compute_price_unit_and_date_planned_and_name(self):
        po_lines_without_requisition = self.env['purchase.order.line']
        for pol in self:
            if pol.display_type or not pol.requisition_line_id:
                po_lines_without_requisition |= pol
                continue

            requisition_line = pol.requisition_line_id
            pol.price_unit = requisition_line.uom_id._compute_price(requisition_line.price_unit, pol.uom_id)
            partner = pol.order_id.partner_id or requisition_line.requisition_id.vendor_id
            pol.date_planned = pol._get_date_planned({'delay': requisition_line.lead_time})
            seller = requisition_line.supplier_info_ids[:1] or pol.selected_seller_id
            product_ctx = {'seller_id': seller.id, 'lang': get_lang(pol.env, partner.lang).code}
            name = pol._get_product_purchase_description(pol.product_id.with_context(product_ctx))
            if requisition_line.product_description_variants:
                name += '\n' + requisition_line.product_description_variants
            pol.name = name
        super(PurchaseOrderLine, po_lines_without_requisition)._compute_price_unit_and_date_planned_and_name()
