# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, get_lang


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    requisition_id = fields.Many2many(
        'purchase.requisition',
        relation='purchase_order_requisition_rel',
    )
    requisition_type = fields.Selection(related='requisition_id.requisition_type')
    date_order_warning = fields.Char(compute='_compute_date_order_warning')

    @api.depends('date_order', 'requisition_id.date_start', 'requisition_id.date_end')
    def _compute_date_order_warning(self):
        for order in self:
            if not order.date_order:
                order.date_order_warning = False
                continue
            order_date = order.date_order.date()
            violating_requisitions = order.requisition_id.filtered(
                lambda r: (r.date_start and order_date < r.date_start) or
                            (r.date_end and order_date > r.date_end)
            ).mapped('name')
            if not violating_requisitions:
                order.date_order_warning = False
            else:
                order.date_order_warning = _("You are placing an order outside the %s validity period", ", ".join(violating_requisitions))

    @api.onchange('requisition_id')
    def _onchange_requisition_id(self):

        self = self.with_company(self.company_id)
        requisition = self.requisition_id

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
        # Do not clobber existing lines if the PO is already confirmed
        if self.state != 'draft':
            return
        order_lines = []
        existing_req_lines = self.order_line.requisition_line_id._origin
        for req in requisition:
            for line in req.line_ids:
                # skip lines already added
                if line._origin in existing_req_lines:
                    print('already present')
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

    requisition_line_id = fields.Many2one(
        'purchase.requisition.line',
        ondelete='set null',
        index=True,
    )
    order_too_big_warning = fields.Char(compute='_compute_order_too_big_warning')

    @api.depends('product_qty')
    def _compute_order_too_big_warning(self):
        for line in self:
            line.order_too_big_warning = False
            req_line = line.requisition_line_id
            if not req_line:
                continue

            is_exceeded = (
                req_line.remaining_qty < 0
                if line.order_id.state == 'purchase'
                else line.product_qty > req_line.remaining_qty
            )
            if is_exceeded:
                line.order_too_big_warning = _(
                    "Ordering this quantity will make the total ordered quantity for %s exceed the agreed-upon quantity",
                    req_line.requisition_id.display_name,
                )

    def _compute_price_unit_and_date_planned_and_name(self):
        po_lines_without_requisition = self.env['purchase.order.line']
        for pol in self:
            if pol.display_type or not pol.requisition_line_id:
                po_lines_without_requisition |= pol
                continue

            requisition_line = pol.requisition_line_id
            pol.price_unit = requisition_line.uom_id._compute_price(requisition_line.price_unit, pol.uom_id)
            partner = pol.order_id.partner_id or requisition_line.requisition_id.vendor_id
            if pol.selected_seller_id or not pol.date_planned:
                pol.date_planned = pol._get_date_planned(pol.selected_seller_id._get_seller_info())
            product_ctx = {'seller_id': pol.selected_seller_id.id, 'lang': get_lang(pol.env, partner.lang).code}
            name = pol._get_product_purchase_description(pol.product_id.with_context(product_ctx))
            if requisition_line.product_description_variants:
                name += '\n' + requisition_line.product_description_variants
            pol.name = name
        super(PurchaseOrderLine, po_lines_without_requisition)._compute_price_unit_and_date_planned_and_name()
