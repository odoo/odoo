# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from markupsafe import Markup

from odoo import _, api, fields, models


class DeliveryNote(models.Model):
    _name = "delivery.note"
    _inherit = ['mail.thread', 'delivery.tracker']
    _description = "Delivery Note"

    backorder_id = fields.Many2one(
        string='Back Order of',
        help="If this shipment was split, links to the original shipment.",
        comodel_name='delivery.note',
        readonly=True,
        copy=False,
        index='btree_not_null',
        check_company=True,
    )
    backorder_ids = fields.One2many('delivery.note', 'backorder_id', 'Back Orders')
    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company',
        default=lambda self: self.env.company,
        store=True,
        readonly=True,
        index=True,
    )
    note_line_ids = fields.One2many(
        string='Operations',
        comodel_name='delivery.note.line',
        inverse_name='note_id',
    )
    name = fields.Char(string='Reference', default='/', readonly=True, copy=False)
    origin = fields.Char('Source Document', index='trigram')
    partner_id = fields.Many2one(
        string='Contact',
        comodel_name='res.partner',
        related='sale_order_id.partner_id',
        check_company=True,
    )
    sale_order_id = fields.Many2one(
        string='Sales Order', comodel_name='sale.order', check_company=True
    )
    shipping_date = fields.Datetime(
        'Shipping Date',
        help="Date at which the delivery has been processed.",
        default=fields.Datetime.now,
        copy=False,
    )
    signature = fields.Image(
        'Signature', help='Signature', attachment=True, default=None, copy=False
    )
    user_id = fields.Many2one(
        string='Responsible',
        comodel_name='res.users',
        domain=lambda self: [
            ('all_group_ids', 'in', self.env.ref('sales_team.group_sale_salesman').id)
        ],
        default=lambda self: self.env.user,
        copy=False,
        tracking=True,
    )

    # === COMPUTE METHODS ===#

    @api.depends(
        'partner_id',
        'carrier_id.max_weight',
        'carrier_id.max_volume',
        'carrier_id.must_have_tag_ids',
        'carrier_id.excluded_tag_ids',
    )
    def _compute_allowed_carrier_ids(self):
        for note in self:
            carriers = self.env['delivery.carrier'].search(
                self.env['delivery.carrier']._check_company_domain(note.company_id)
            )
            note.allowed_carrier_ids = (
                carriers.available_carriers(note.partner_id, note) if note.partner_id else carriers
            )

    # === CRUD METHODS ===#

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                seq_date = (
                    fields.Datetime.context_timestamp(
                        self, fields.Datetime.to_datetime(vals['shipping_date'])
                    )
                    if 'shipping_date' in vals
                    else None
                )
                vals['name'] = (
                    self
                    .env['ir.sequence']
                    .with_company(vals.get('company_id'))
                    .next_by_code('delivery.note', sequence_date=seq_date)
                    or '/'
                )

        return super().create(vals_list)

    # === BUSINESS METHODS ===#

    def delivery_note_confirm(self):
        for note in self:
            # Generate the message to be posted on the sale_order
            msg = _("A shipment has been confirmed with %s including:", note.carrier_id.name)
            product_lines = Markup("<br>").join([
                _(
                    "- %(quantity)d %(name)s",
                    quantity=line.product_uom_qty,
                    name=line.product_id.display_name,
                )
                for line in note.note_line_ids
                if line.product_uom_qty > 0
            ])
            tracking_url = note.carrier_tracking_url
            tracking_url_line = (
                Markup('<br><br><a href="%s">%s</a>') % (tracking_url, _("Track Shipping"))
                if tracking_url
                else ''
            )

            message_post = Markup('%s<br><br>%s%s') % (msg, product_lines, tracking_url_line)

            # If nothing delivered, do nothing
            if not product_lines:
                continue

            # Create the backorder and set the delivered quantities on the sale order
            note._create_backorder_and_set_quantities()

            # Set the delivery line as delivered
            for line in note.sale_order_id.order_line:
                if line.is_delivery:
                    line.qty_delivered = line.product_uom_qty

            # Post the message on the sale order and send the confirmation email
            note.sale_order_id.message_post(body=message_post)
            note._send_confirmation_email()

    def delivery_note_cancel(self):
        self.unlink()

    def _find_mail_template(self):
        return self.env.ref(
            'delivery.mail_template_data_delivery_confirmation', raise_if_not_found=False
        )

    def _send_confirmation_email(self):
        subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')
        for note in self:
            delivery_template = note._find_mail_template()
            note.with_context(force_send=True).message_post_with_source(
                delivery_template,
                message_type='comment',
                email_layout_xmlid='mail.mail_notification_light',
                subtype_id=subtype_id,
            )
            # move the mail thread to the sale order
            note.message_change_thread(note.sale_order_id)
            # move attachments
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'delivery.note'),
                ('res_id', '=', note.id),
            ])
            attachments.sudo().write({'res_model': 'sale.order', 'res_id': note.sale_order_id.id})

    def _create_backorder_and_set_quantities(self):
        """For each line, set the delivered quantity on the sale order. If the delivered quantity
        is less than the ordered quantity, create a backorder with the remaining quantity."""
        self.ensure_one()
        backorder = False
        backorder_lines = []
        for line in self.note_line_ids:
            # Set the delivered quantity on the sale order
            line.sale_order_line_id.qty_delivered += line.product_uom_qty
            if line.product_uom_qty < line.quantity_ordered:
                # Create the backorder if not already created
                if not backorder:
                    backorder = self.env['delivery.note'].create({
                        'backorder_id': self.id,
                        'name': "Backorder for %s" % self.sale_order_id.name,
                        'partner_id': self.sale_order_id.partner_id.id,
                        'carrier_id': self.carrier_id.id,
                        'carrier_tracking_ref': self.carrier_tracking_ref,
                        'sale_order_id': self.sale_order_id.id,
                        'origin': self.sale_order_id.name,
                    })
                # Create the backorder line
                backorder_line = self.env['delivery.note.line'].create({
                    'note_id': self.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'product_uom_qty': line.quantity_ordered - line.product_uom_qty,
                    'quantity_ordered': line.quantity_ordered - line.product_uom_qty,
                })
                backorder_lines.append(backorder_line.id)

        # If there is a backorder, link it to the delivery note
        if backorder_lines:
            backorder.note_line_ids = backorder_lines
            self.backorder_ids = [backorder.id]

    def _get_report_lang(self):
        """Determine language to use for translated description."""
        return self.partner_id.lang or self.env.lang

    def get_multiple_carrier_tracking(self):
        self.ensure_one()
        try:
            return json.loads(self.carrier_tracking_url)
        except (ValueError, TypeError):
            return False
