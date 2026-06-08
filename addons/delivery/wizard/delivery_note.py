# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class DeliveryNoteWizard(models.TransientModel):
    _name = "delivery.note.wizard"
    _description = "Delivery Note Wizard"

    name = fields.Char(string="Note Reference", default="/")
    note_line_ids = fields.One2many(
        string="Operations", comodel_name="delivery.note.wizard.line", inverse_name="note_id"
    )
    dm_id = fields.Many2one(
        string="Delivery method", comodel_name="delivery.carrier", check_company=True
    )
    tracking_ref = fields.Char(string="Tracking Reference")
    tracking_url = fields.Char(string="Tracking URL", compute="_compute_tracking_url")
    shipping_date = fields.Date(string="Shipping Date", default=fields.Date.today)
    so_id = fields.Many2one(string="Sales Order", comodel_name="sale.order")
    so_reference = fields.Char(string="Order reference", related="so_id.name")
    company_id = fields.Many2one(related="so_id.company_id")
    partner_id = fields.Many2one(comodel_name="res.partner", related="so_id.partner_id")

    # === COMPUTE METHODS ===#

    @api.depends("dm_id", "tracking_ref")
    def _compute_tracking_url(self):
        for note in self:
            if note.dm_id.tracking_url and note.tracking_ref:
                note.tracking_url = note.dm_id.tracking_url.replace(
                    "<shipmenttrackingnumber>", note.tracking_ref
                )
            else:
                note.tracking_url = False

    # === BUSINESS METHODS ===#

    def action_confirm(self):
        for note in self:
            lines_to_ship = note.note_line_ids.filtered(lambda _line: _line.product_uom_qty)
            if not lines_to_ship:  # No products to ship.
                continue

            note.name = self.env["ir.sequence"].next_by_code("delivery.note.wizard")
            note._send_shipping_confirmation_email()
            lines_to_ship._update_sol_qty_delivered()

            # Set the delivery line as delivered
            for line in note.so_id.order_line.filtered("is_delivery"):
                line.qty_delivered = line.product_uom_qty

    def _send_shipping_confirmation_email(self):
        """Send an email to the customer confirming the shipment."""
        self.ensure_one()
        delivery_note_template = self.env.ref(
            "delivery.mail_template_data_delivery_note", raise_if_not_found=False
        )
        if delivery_note_template:
            rendered_template = delivery_note_template._generate_template(
                [self.id], ["body_html", "subject", "partner_to"]
            )[self.id]
            rendered_attachments = delivery_note_template._generate_template_attachments(
                [self.id], ["report_template_ids"]
            )[self.id]
            self.so_id.message_post(
                body=rendered_template["body_html"],
                subject=rendered_template["subject"],
                partner_ids=rendered_template.get("partner_ids", []),
                attachments=rendered_attachments.get("attachments", []),
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )

    def _get_report_lang(self):
        return self.partner_id.lang or self.env.lang
