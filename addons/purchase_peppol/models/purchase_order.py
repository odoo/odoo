from odoo import fields, models
from odoo.exceptions import ValidationError


# Replace Enum with simple constant classes
class OrderState:
    DRAFT = "draft"
    PENDING = "pending_response"
    CONFIRMED = "confirmed"
    CHANGE_PENDING = "change_pending"
    CANCEL_PENDING = "cancellation_pending"
    CANCELLED = "cancelled"


class Event:
    SEND_ORDER = "send_t01"
    SEND_CHANGE = "send_t114"
    SEND_CANCEL = "send_t115"
    RECEIVE_AB = "receive_t116_ab"
    RECEIVE_AP = "receive_t116_ap"
    RECEIVE_RE = "receive_t116_re"


# TRANSITIONS now uses string constants
TRANSITIONS = {
    (OrderState.DRAFT, Event.SEND_ORDER): (OrderState.PENDING, None),
    (OrderState.PENDING, Event.RECEIVE_AP): (OrderState.CONFIRMED, '_on_peppol_order_confirm'),
    (OrderState.PENDING, Event.RECEIVE_RE): (OrderState.CANCELLED, '_on_peppol_order_reject'),

    # Order change flow
    (OrderState.CONFIRMED, Event.SEND_CHANGE): (OrderState.CHANGE_PENDING, None),
    (OrderState.CHANGE_PENDING, Event.RECEIVE_AP): (OrderState.CONFIRMED, '_on_peppol_order_change_confirm'),
    (OrderState.CHANGE_PENDING, Event.RECEIVE_RE): (OrderState.CONFIRMED, '_on_peppol_order_change_reject'),

    # Order cancel flow
    (OrderState.CONFIRMED, Event.SEND_CANCEL): (OrderState.CANCEL_PENDING, None),
    (OrderState.CANCEL_PENDING, Event.RECEIVE_AP): (OrderState.CONFIRMED, '_on_peppol_order_cancel_reject'),
    (OrderState.CANCEL_PENDING, Event.RECEIVE_RE): (OrderState.CANCELLED, '_on_peppol_order_cancel_confirm'),
}


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    peppol_order_id = fields.Char(string="PEPPOL order document ID")
    l10n_sg_peppol_advanced_order_state = fields.Selection(
        [
            (OrderState.DRAFT, "Draft"),
            (OrderState.PENDING, "Pending Response"),
            (OrderState.CONFIRMED, "Confirmed"),
            (OrderState.CHANGE_PENDING, "Change Request Sent"),
            (OrderState.CANCEL_PENDING, "Cancellation Request Sent"),
            (OrderState.CANCELLED, "Cancelled"),
        ],
        string="PEPPOL Advanced Order Status",
        default=OrderState.DRAFT,
    )
    edi_tracker_ids = fields.One2many(
        'purchase.peppol.advanced.order.tracker',
        'order_id',
        string="EDI Trackers",
    )

    def process_event(self, event):
        """
        Updates the order's advanced order state according to `order_response_code` and order's
        current advanced order state.
        """
        # Apply per-record so each order's current state is considered and callbacks executed
        for order in self:
            key = (order.l10n_sg_peppol_advanced_order_state, event)
            if key not in TRANSITIONS:
                raise ValidationError(self.env._(
                    "Invalid event %s for order state %s",
                    event,
                    order.l10n_sg_peppol_advanced_order_state,
                ))
            new_state, callback = TRANSITIONS[key]
            order.l10n_sg_peppol_advanced_order_state = new_state
            if callback:
                # call the callback on the specific order record
                getattr(order, callback)()

    # -------------------------------------------------------------------------
    # Business logics triggered by PEPPOL Order Response Advanced
    # -------------------------------------------------------------------------

    def _on_peppol_order_confirm(self):
        order_tracker = self.edi_tracker_ids.search([('document_type', '=', 'order')], limit=1)
        order_tracker.state = 'accepted'

        if self.state in ['draft', 'sent']:
            self.write({'state': 'purchase', 'date_approve': fields.Datetime.now()})
        if self.lock_confirmed_po == 'lock':
            self.write({'locked': True})
        self.message_post(body=self.env._("Order is accepted by the seller."))

    def _on_peppol_order_reject(self):
        order_tracker = self.edi_tracker_ids.search([('document_type', '=', 'order')], limit=1)
        order_tracker.state = 'rejected'

        if any(move.state not in ('cancel', 'draft') for move in self.invoice_ids):
            self.message_post(body=self.env._(
                "Received order rejection via PEPPOL but was unable to cancel this order. You must"
                " first cancel their related vendor bills and manually cancel this order.",
            ))
            return
        self.message_post(body=self.env._("Order is rejected by the seller."))
        self.write({'state': 'cancel'})

    def _on_peppol_order_change_confirm(self):
        order_tracker = self.edi_tracker_ids.search([('document_type', '=', 'order_change')], limit=1)
        order_tracker.state = 'accepted'

        self.message_post(body=self.env._("Order change request is accepted by the seller."))

    def _on_peppol_order_change_reject(self):
        order_tracker = self.edi_tracker_ids.search([('document_type', '=', 'order_change')], limit=1)
        order_tracker.state = 'rejected'

        self.message_post(body=self.env._("Order change request is rejected by the seller."))

        # Revert the changes back to the last applied EDI order document
        # TODO: Implement reverting logic
        last_applied_order = next(t for t in self.edi_tracker_ids if t.state == 'accepted')
        if last_applied_order.document_type == 'order':
            xml_tree = self._to_files_data(last_applied_order.attachment_id)[0]['xml_tree']
            order_vals, logs = self.env['purchase.edi.xml.ubl_bis3_order']._retrieve_order_vals(self, xml_tree)
        elif last_applied_order.document_type == 'order_change':
            xml_tree = self._to_files_data(last_applied_order.attachment_id)
            self.env['purchase.edi.xml.ubl_bis3_order_change']._retrieve_order_vals(self, xml_tree)

    def _on_peppol_order_cancel_confirm(self):
        order_tracker = self.edi_tracker_ids.search([('document_type', '=', 'order_cancel')], limit=1)
        order_tracker.state = 'accepted'

        if any(move.state not in ('cancel', 'draft') for move in self.invoice_ids):
            self.message_post(body=self.env._(
                "Received order rejection via PEPPOL but was unable to cancel this order. You must"
                " first cancel their related vendor bills and manually cancel this order.",
            ))
            return
        self.message_post(body=self.env._("Order cancellation request is accepted by the seller."))
        self.write({'state': 'cancel'})

    def _on_peppol_order_cancel_reject(self):
        order_tracker = self.edi_tracker_ids.search([('document_type', '=', 'order_cancel')], limit=1)
        order_tracker.state = 'rejected'

        if self.state in ['draft', 'sent']:
            self.write({'state': 'purchase', 'date_approve': fields.Datetime.now()})
        if self.lock_confirmed_po == 'lock':
            self.write({'locked': True})
        self.message_post(body=self.env._("Order cancellation request is rejected by the seller."))

    def action_send_advanced_order(self):
        self.process_event(Event.SEND_ORDER)
        order_xml = self.env['purchase.edi.xml.ubl_bis3_order'].build_order_xml(self)

        attachment = self.env['ir.attachment'].create({
            'name': f"{self.name}-ubl_bis3_order.xml",
            'raw': order_xml,
            'type': 'binary',
            'mimetype': "application/xml",
            'res_model': 'purchase.order',
            'res_id': self.id,
        })
        # Mock send
        print("@@!!@@ Order request sent @@!!@@")

        self.env['purchase.peppol.advanced.order.tracker'].create({
            'order_id': self.id,
            'attachment_id': attachment.id,
            'state': 'sent',
            'document_type': 'order',
            'sequence': 0,  # Only one order per entire transaction flow
        })

    def action_send_order_change(self):
        self.process_event(Event.SEND_CHANGE)
        order_xml = self.env['purchase.edi.xml.ubl_bis3_order_change'].build_order_change_xml(self)
        order_change_seq = len([t for t in self.edi_tracker_ids if t.document_type == 'order_change']) + 1

        attachment = self.env['ir.attachment'].create({
            'name': f"{self.name}-ubl_bis3_order_change-{order_change_seq}.xml",
            'raw': order_xml,
            'type': 'binary',
            'mimetype': "application/xml",
            'res_model': 'purchase.order',
            'res_id': self.id,
        })
        # Mock send
        print("@@!!@@ Order request sent @@!!@@")

        self.env['purchase.peppol.advanced.order.tracker'].create({
            'order_id': self.id,
            'attachment_id': attachment.id,
            'state': 'sent',
            'document_type': 'order_change',
            'sequence': self.edi_tracker_ids[:1].sequence + 1,
        })

    def action_send_order_cancel(self):
        self.process_event(Event.SEND_CANCEL)
        order_xml = self.env['purchase.edi.xml.ubl_bis3_order_cancel'].build_order_cancel_xml(self)

        attachment = self.env['ir.attachment'].create({
            'name': f"{self.name}-ubl_bis3_order_cancel.xml",
            'raw': order_xml,
            'type': 'binary',
            'mimetype': "application/xml",
            'res_model': 'purchase.order',
            'res_id': self.id,
        })
        # Mock send
        print("@@!!@@ Order request sent @@!!@@")

        self.env['purchase.peppol.advanced.order.tracker'].create({
            'order_id': self.id,
            'attachment_id': attachment.id,
            'state': 'sent',
            'document_type': 'order_cancel',
            'sequence': 0,
        })
