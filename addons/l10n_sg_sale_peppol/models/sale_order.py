from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_date
from base64 import b64encode


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    l10n_sg_peppol_message_uuid = fields.Char(string='InvoiceNow (Peppol) Message ID')
    l10n_sg_peppol_order_id = fields.Char(string="InvoiceNow (Peppol) Order Document ID")
    l10n_sg_peppol_buyer_endpoint = fields.Char(string="InvoiceNow (Peppol) Buyer Endpoint", readonly=True)
    l10n_sg_peppol_order_tx_ids = fields.One2many(
        'sale.peppol.advanced.order.transaction',
        'order_id',
        string="EDI Trackers",
    )

    l10n_sg_has_pending_order_change = fields.Boolean(compute='_has_pending_order_change')
    l10n_sg_has_pending_order_cancel = fields.Boolean(compute='_has_pending_order_cancel')

    @api.model
    def _peppol_create_order_from_attachment(self, attachments):
        """Create sale order(s) from PEPPOL attachment(s) using the PEPPOL-specific decoder
        (no price_unit recomputation). Bypasses _get_edi_decoder by pre-setting decoder_info,
        so manual file import continues to use the standard decoder with price recompute.
        """
        grouping_method = self._group_files_data_by_origin_attachment
        files_data = self._to_files_data(attachments)
        files_data.extend(self._unwrap_attachments(files_data))
        file_data_groups = grouping_method(files_data)

        records = self.create([{}] * len(file_data_groups))
        peppol_decoder_info = {
            'priority': 30,
            'decoder': self.env['sale.edi.xml.ubl_bis3_advanced_order']._peppol_import_order_ubl,
        }
        for record, file_data_group in zip(records, file_data_groups):
            for file_data in file_data_group:
                file_data['decoder_info'] = peppol_decoder_info
            attachment_records = self._from_files_data(file_data_group)
            attachment_records.write({
                'res_model': record._name,
                'res_id': record.id,
            })
            record.message_post(
                body=self.env._("This document was created from the following attachment(s)."),
                attachment_ids=attachment_records.ids,
            )

        for record, file_data_group in zip(records, file_data_groups):
            record._extend_with_attachments(file_data_group, new=True)

        return records

    def action_confirm(self):
        """EXTENDS 'sale': confirming a quotation received through Peppol accepts the order."""
        res = super().action_confirm()
        for order in self:
            if order_tx := order._l10n_sg_peppol_get_pending_tx('order'):
                order._l10n_sg_peppol_reply(order_tx, 'AP', 'accepted')
        return res

    def _action_cancel(self):
        """EXTENDS 'sale': cancelling a quotation received through Peppol rejects the order."""
        res = super()._action_cancel()
        for order in self:
            order_tx = order._l10n_sg_peppol_get_pending_tx('order')
            if not order_tx:
                continue
            if order._l10n_sg_peppol_get_pending_tx('order_cancel'):
                # The buyer withdrew the order: the reply to the cancellation request is enough.
                order_tx.activity_id.filtered('active').unlink()
            else:
                order._l10n_sg_peppol_reply(order_tx, 'RE', 'rejected')
        return res

    def action_apply_peppol_order_change(self):
        for order in self:
            order_change_tx = order._l10n_sg_peppol_get_pending_tx('order_change')
            if not order_change_tx:
                raise UserError(order.env._("There is no pending order change request for this order."))

            self.env['sale.edi.xml.ubl_bis3_order_change'].process_peppol_order_change(order, order_change_tx.attachment_id)
            order._l10n_sg_peppol_reply(order_change_tx, 'AP', 'accepted')

    def action_reject_peppol_order_change(self):
        for order in self:
            order_change_tx = order._l10n_sg_peppol_get_pending_tx('order_change')
            if not order_change_tx:
                raise UserError(order.env._("There is no pending order change request for this order."))

            order._l10n_sg_peppol_reply(order_change_tx, 'RE', 'rejected')

    def action_apply_peppol_order_cancel(self):
        for order in self:
            order_cancel_tx = order._l10n_sg_peppol_get_pending_tx('order_cancel')
            if not order_cancel_tx:
                raise UserError(order.env._("There is no pending order cancellation request for this order."))

            self.env['sale.edi.xml.ubl_bis3_order_cancel'].process_peppol_order_cancel(order, order_cancel_tx.attachment_id)
            order._l10n_sg_peppol_reply(order_cancel_tx, 'RE', 'accepted')

    def action_reject_peppol_order_cancel(self):
        for order in self:
            order_cancel_tx = order._l10n_sg_peppol_get_pending_tx('order_cancel')
            if not order_cancel_tx:
                raise UserError(order.env._("There is no pending order cancellation request for this order."))

            order._l10n_sg_peppol_reply(order_cancel_tx, 'AP', 'rejected')

    def _l10n_sg_peppol_get_pending_tx(self, document_type):
        """Return the latest transaction of `document_type` waiting for a reply."""
        self.ensure_one()
        return self.l10n_sg_peppol_order_tx_ids.filtered_domain([
            ('document_type', '=', document_type),
            ('state', '=', 'to_reply'),
        ]).sorted()[:1]

    def _l10n_sg_peppol_schedule_review(self, order_tx, note):
        """Schedule an activity asking the salesperson to reply to `order_tx`."""
        self.ensure_one()
        summary = {
            'order': self.env._("Review InvoiceNow (Peppol) order"),
            'order_change': self.env._("Review InvoiceNow (Peppol) order change"),
            'order_cancel': self.env._("Review InvoiceNow (Peppol) order cancellation"),
        }[order_tx.document_type]
        # Orders received through Peppol are created by the cron, as OdooBot; fall back on the
        # responsible set on the activity type in that case.
        salesperson = self.user_id.filtered(lambda user: not user._is_superuser())
        # The buyer's deadline to accept the order (cac:ValidityPeriod) is informative only: it
        # becomes the due date of the review.
        response_deadline = False
        if order_tx.document_type == 'order':
            tree = self.env['account.move']._to_files_data(order_tx.attachment_id)[0]['xml_tree']
            try:
                response_deadline = fields.Date.to_date(tree.findtext('./{*}ValidityPeriod/{*}EndDate'))
            except ValueError:
                pass
        if response_deadline:
            note = self.env._(
                "%(note)s The buyer expects a response by %(date)s.",
                note=note, date=format_date(self.env, response_deadline),
            )
        order_tx.activity_id = self.activity_schedule(
            'l10n_sg_sale_peppol.mail_activity_type_peppol_order_review',
            date_deadline=response_deadline or None,
            summary=summary,
            note=note,
            user_id=salesperson.id,
        )

    def _l10n_sg_peppol_reply(self, order_tx, code, state):
        """Send the Order Response for `order_tx` and mark its activity as done."""
        self.ensure_one()
        self._send_order_response_advanced(order_tx, code)
        order_tx.state = state
        feedback = {
            ('order', 'accepted'): self.env._("Order accepted"),
            ('order', 'rejected'): self.env._("Order rejected"),
            ('order_change', 'accepted'): self.env._("Order change request accepted"),
            ('order_change', 'rejected'): self.env._("Order change request rejected"),
            ('order_cancel', 'accepted'): self.env._("Order cancellation request accepted"),
            ('order_cancel', 'rejected'): self.env._("Order cancellation request rejected"),
        }[order_tx.document_type, state]
        # The activity may already have been marked as done manually.
        order_tx.activity_id.filtered('active').action_feedback(feedback=feedback)

    def _send_order_response_advanced(self, order_tx, code):
        """Send an Order Response Advanced document to the buyer via PEPPOL.

        :param order_tx: PEPPOL advanced order transaction to respond to
        :param code: Response code (AP=Accepted, RE=Rejected, AB=Automatically Accepted, CA=Conditionally Accepted)
        """
        order_response_xml = self.env['sale.edi.xml.ubl_bis3_order_response_advanced'].build_order_response_xml(self, order_tx, code)
        params = {
            'documents': [{
                'filename': f"{self.name}-{order_tx.document_type}-response-{order_tx.id}.xml",
                'ubl': b64encode(order_response_xml).decode(),
                'receiver': self.l10n_sg_peppol_buyer_endpoint,
            }],
        }

        edi_user = self.company_id.account_peppol_edi_user

        edi_user._call_peppol_proxy(
            "/api/peppol/1/send_document",
            params=params,
        )

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends('l10n_sg_peppol_order_tx_ids.state')
    def _has_pending_order_change(self):
        for order in self:
            order.l10n_sg_has_pending_order_change = bool(order._l10n_sg_peppol_get_pending_tx('order_change'))

    @api.depends('l10n_sg_peppol_order_tx_ids.state')
    def _has_pending_order_cancel(self):
        for order in self:
            order.l10n_sg_has_pending_order_cancel = bool(order._l10n_sg_peppol_get_pending_tx('order_cancel'))
