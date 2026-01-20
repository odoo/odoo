from base64 import b64encode

from odoo import _, api, fields, models, modules, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import (
    AccountEdiProxyError,
)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    l10n_sg_peppol_order_id = fields.Char(string='PEPPOL order document ID')
    l10n_sg_peppol_order_tx_ids = fields.One2many(
        'purchase.peppol.advanced.order.transaction',
        'order_id',
        string='EDI Transactions',
    )

    # -------------------------------------------------------------------------
    # PEPPOL SEND HELPERS
    # -------------------------------------------------------------------------

    l10n_sg_peppol_can_send_order = fields.Boolean(compute='_compute_l10n_sg_peppol_can_send_order')
    l10n_sg_peppol_can_send_order_change = fields.Boolean(compute='_compute_l10n_sg_peppol_can_send_order_change')
    l10n_sg_peppol_can_send_order_cancel = fields.Boolean(compute='_compute_l10n_sg_peppol_can_send_order_cancel')
    l10n_sg_peppol_can_send_order_balance = fields.Boolean(compute='_compute_l10n_sg_peppol_can_send_order_balance')

    def _l10n_sg_peppol_get_sender_edi_user(self):
        """Return the Peppol EDI user used to send documents for this order's company.

        Handles the "branch uses parent company Peppol connection" setup.
        """
        self.ensure_one()
        company = self.company_id
        parent_company = company._get_active_peppol_parent_company()
        sender_company = parent_company or company
        return sender_company.account_peppol_edi_user

    def _l10n_sg_peppol_get_receiver_identifier(self):
        """Return the receiver identifier in the form 'EAS:Endpoint'."""
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id.with_company(self.company_id)
        if not (partner.routing_scheme and partner.routing_endpoint):
            raise UserError(
                _(
                    'Missing Peppol receiver details on the vendor.\n'
                    "Please set 'Peppol EAS' and 'Peppol Endpoint' on %(partner)s.",
                    partner=partner.display_name,
                )
            )
        return partner.routing_identifier

    def _l10n_sg_peppol_send_document(self, *, filename: str, xml_bytes: bytes):
        """Send one UBL document through the Peppol proxy.

        :returns: message_uuid (str)
        """
        self.ensure_one()

        edi_user = self._l10n_sg_peppol_get_sender_edi_user()
        if not edi_user:
            raise UserError(
                _(
                    'Peppol is not configured for %(company)s.\n'
                    'Please register this company as a Peppol sender first.',
                    company=self.company_id.display_name,
                )
            )

        receiver_identifier = self._l10n_sg_peppol_get_receiver_identifier()
        params = {
            'documents': [
                {
                    'filename': filename,
                    'receiver': receiver_identifier,
                    'ubl': b64encode(xml_bytes).decode(),
                }
            ],
        }

        # Avoid real HTTP in automated test suites unless explicitly requested.
        if (
            modules.module.current_test or tools.config.get('test_enable')
        ) and not self.env.context.get('force_peppol_send'):
            return 'test-skip'

        response = edi_user._call_peppol_proxy(
            '/api/peppol/1/send_document', params=params
        )
        if error_vals := response.get('error'):
            # ParticipantNotReady and other structured errors are mapped by _call_peppol_proxy,
            # but keep a safeguard if server returns an "error" payload without raising.
            raise UserError(edi_user._get_peppol_error_message(error_vals))
        return response['messages'][0]['message_uuid']

    def _l10n_sg_peppol_has_accepted_order(self):
        self.ensure_one()
        return any(
            t.document_type == 'order' and t.state == 'accepted'
            for t in self.l10n_sg_peppol_order_tx_ids
        )

    def _l10n_sg_peppol_has_accepted_order_cancel(self):
        self.ensure_one()
        return any(
            t.document_type == 'order_cancel' and t.state == 'accepted'
            for t in self.l10n_sg_peppol_order_tx_ids
        )

    @api.depends('l10n_sg_peppol_order_tx_ids')
    def _compute_l10n_sg_peppol_can_send_order(self):
        for order in self:
            order.l10n_sg_peppol_can_send_order = not order.l10n_sg_peppol_order_tx_ids

    @api.depends('l10n_sg_peppol_order_tx_ids', 'l10n_sg_peppol_order_tx_ids.state')
    def _compute_l10n_sg_peppol_can_send_order_change(self):
        for order in self:
            if order._l10n_sg_peppol_has_accepted_order_cancel():
                order.l10n_sg_peppol_can_send_order_change = False
                continue
            has_accepted_order = order._l10n_sg_peppol_has_accepted_order()
            has_pending_change = any(
                t.document_type == 'order_change' and t.state == 'sent'
                for t in order.l10n_sg_peppol_order_tx_ids
            )
            order.l10n_sg_peppol_can_send_order_change = has_accepted_order and not has_pending_change

    @api.depends('l10n_sg_peppol_order_tx_ids', 'l10n_sg_peppol_order_tx_ids.state')
    def _compute_l10n_sg_peppol_can_send_order_cancel(self):
        for order in self:
            if order._l10n_sg_peppol_has_accepted_order_cancel():
                order.l10n_sg_peppol_can_send_order_cancel = False
                continue
            has_accepted_order = order._l10n_sg_peppol_has_accepted_order()
            has_pending_cancel = any(
                t.document_type == 'order_cancel' and t.state == 'sent'
                for t in order.l10n_sg_peppol_order_tx_ids
            )
            order.l10n_sg_peppol_can_send_order_cancel = has_accepted_order and not has_pending_cancel

    @api.depends('order_line.qty_received', 'l10n_sg_peppol_order_tx_ids.state')
    def _compute_l10n_sg_peppol_can_send_order_balance(self):
        for order in self:
            if order._l10n_sg_peppol_has_accepted_order_cancel():
                order.l10n_sg_peppol_can_send_order_balance = False
                continue
            precision = self.env['decimal.precision'].precision_get('Product Unit')
            order.l10n_sg_peppol_can_send_order_balance = any(
                not float_is_zero(line.qty_received, precision_digits=precision)
                for line in order.order_line
            )

    def handle_order_response_advanced(self, order_change_ref, response_code):
        RESPONSE_MESSAGES = {
            ('order', 'AP'): self.env._('Order is accepted by the seller.'),
            ('order_cancel', 'AP'): self.env._('Order cancellation request is rejected by the seller.'),
            ('order_change', 'AP'): self.env._('Order change request is accepted by the seller.'),
            ('order', 'RE'): self.env._('Order is rejected by the seller.'),
            ('order_cancel', 'RE'): self.env._('Order cancellation request is accepted by the seller.'),
            ('order_change', 'RE'): self.env._('Order change request is rejected by the seller.'),
        }

        for order in self:
            if response_code not in ('AB', 'AP', 'RE'):
                raise ValidationError(
                    self.env._('Invalid response code %s', response_code)
                )

            if order_change_ref:
                order_tx = order.l10n_sg_peppol_order_tx_ids.filtered(
                    lambda t: t.order_change_ref == order_change_ref,
                ).sorted()[:1]
            else:  # If order_change_ref is not provided, the response is either for order or order cancellation
                order_tx = order.l10n_sg_peppol_order_tx_ids.filtered(
                    lambda t: t.document_type in ['order', 'order_cancel'],
                ).sorted()[:1]

            if response_code == 'AP':
                state = 'rejected' if order_tx.document_type == 'order_cancel' else 'accepted'
                order_tx.state = state
                order._on_peppol_order_confirm()

            elif response_code == 'RE':
                state = 'accepted' if order_tx.document_type == 'order_cancel' else 'rejected'
                order_tx.state = state

                # Handling order change rejection is a bit different from order/order cancellation rejection:
                # 1. It is order change "proposal" rejection, not order rejection.
                # 2. Hence we need to revert the order to the last accepted order transaction.
                if order_tx.document_type == 'order_change':
                    order._on_peppol_order_change_reject()
                else:
                    order._on_peppol_order_reject()
            # AB: no state/callback change

            message = RESPONSE_MESSAGES.get((order_tx.document_type, response_code))
            if message:
                order.message_post(body=message)

    # -------------------------------------------------------------------------
    # Business logics triggered by PEPPOL Order Response Advanced
    # -------------------------------------------------------------------------

    def _on_peppol_order_confirm(self):
        self.ensure_one()

        if self.state in ['draft', 'sent']:
            self.write({'state': 'purchase', 'date_approve': fields.Datetime.now()})
        if self.lock_confirmed_po == 'lock':
            self.write({'locked': True})

    def _on_peppol_order_reject(self):
        if any(move.state not in ('cancel', 'draft') for move in self.invoice_ids):
            self.message_post(
                body=self.env._(
                    'Received order rejection via PEPPOL but was unable to cancel this order. You must'
                    ' first cancel their related vendor bills and manually cancel this order.',
                )
            )
            return
        self.write({'state': 'cancel'})

    def _on_peppol_order_change_reject(self):
        last_applied_order = next(
            t for t in self.l10n_sg_peppol_order_tx_ids if t.state == 'accepted'
        )
        self.env['purchase.edi.xml.ubl_bis3_order_change'].revert_order_change(
            self, last_applied_order
        )

    def action_send_advanced_order(self):
        order_xml = self.env['purchase.edi.xml.ubl_bis3_order'].build_order_xml(self)

        attachment = self.env['ir.attachment'].create(
            {
                'name': f'{self.name}-ubl_bis3_order.xml',
                'raw': order_xml,
                'type': 'binary',
                'mimetype': 'application/xml',
                'res_model': 'purchase.order',
                'res_id': self.id,
            }
        )

        self.l10n_sg_peppol_order_id = self.name
        try:
            message_uuid = self._l10n_sg_peppol_send_document(
                filename=attachment.name,
                xml_bytes=order_xml,
            )
            self.message_post(
                body=_('Order request sent via Peppol.'), attachment_ids=[attachment.id]
            )
            proxy_state = 'processing' if message_uuid != 'test-skip' else 'skipped'
        except (AccountEdiProxyError, UserError) as e:
            message_uuid = False
            proxy_state = 'error'
            error_msg = e.message if isinstance(e, AccountEdiProxyError) else str(e)
            self.message_post(
                body=self.env._(
                    'Failed to send order request via Peppol: %s',
                    error_msg,
                ),
                attachment_ids=[attachment.id],
            )

        self.env['purchase.peppol.advanced.order.transaction'].create(
            {
                'order_id': self.id,
                'attachment_id': attachment.id,
                'state': 'sent',
                'document_type': 'order',
                'peppol_message_uuid': message_uuid,
                'peppol_proxy_state': proxy_state,
                'sequence': 0,  # Only one order per entire transaction flow
            }
        )

    def action_send_order_change(self):
        order_change_vals = self.env[
            'purchase.edi.xml.ubl_bis3_order_change'
        ].build_order_change(self)
        order_xml = order_change_vals['xml_content']
        order_change_id = order_change_vals['order_change_id']
        order_sequence_id = order_change_vals['sequence_number_id']

        attachment = self.env['ir.attachment'].create(
            {
                'name': f'{self.name}-ubl_bis3_order_change-{order_sequence_id}.xml',
                'raw': order_xml,
                'type': 'binary',
                'mimetype': 'application/xml',
                'res_model': 'purchase.order',
                'res_id': self.id,
            }
        )
        try:
            message_uuid = self._l10n_sg_peppol_send_document(
                filename=attachment.name,
                xml_bytes=order_xml,
            )
            self.message_post(
                body=_('Order change request sent via Peppol.'),
                attachment_ids=[attachment.id],
            )
            proxy_state = 'processing' if message_uuid != 'test-skip' else 'skipped'
        except (AccountEdiProxyError, UserError) as e:
            message_uuid = False
            proxy_state = 'error'
            error_msg = e.message if isinstance(e, AccountEdiProxyError) else str(e)
            self.message_post(
                body=self.env._(
                    'Failed to send order change request via Peppol: %s',
                    error_msg,
                ),
                attachment_ids=[attachment.id],
            )

        self.env['purchase.peppol.advanced.order.transaction'].create(
            {
                'order_id': self.id,
                'order_change_ref': order_change_id,
                'attachment_id': attachment.id,
                'state': 'sent',
                'document_type': 'order_change',
                'peppol_message_uuid': message_uuid,
                'peppol_proxy_state': proxy_state,
                'sequence': len(self.l10n_sg_peppol_order_tx_ids),
            }
        )

    def action_send_order_cancel(self):
        order_xml = self.env[
            'purchase.edi.xml.ubl_bis3_order_cancel'
        ].build_order_cancel_xml(self)

        attachment = self.env['ir.attachment'].create(
            {
                'name': f'{self.name}-ubl_bis3_order_cancel.xml',
                'raw': order_xml,
                'type': 'binary',
                'mimetype': 'application/xml',
                'res_model': 'purchase.order',
                'res_id': self.id,
            }
        )
        try:
            message_uuid = self._l10n_sg_peppol_send_document(
                filename=attachment.name,
                xml_bytes=order_xml,
            )
            self.message_post(
                body=_('Order cancellation request sent via Peppol.'),
                attachment_ids=[attachment.id],
            )
            proxy_state = 'processing' if message_uuid != 'test-skip' else 'skipped'
        except (AccountEdiProxyError, UserError) as e:
            message_uuid = False
            proxy_state = 'error'
            error_msg = e.message if isinstance(e, AccountEdiProxyError) else str(e)
            self.message_post(
                body=self.env._(
                    'Failed to send order cancellation request via Peppol: %s',
                    error_msg,
                ),
                attachment_ids=[attachment.id],
            )

        self.env['purchase.peppol.advanced.order.transaction'].create(
            {
                'order_id': self.id,
                'attachment_id': attachment.id,
                'state': 'sent',
                'document_type': 'order_cancel',
                'peppol_message_uuid': message_uuid,
                'peppol_proxy_state': proxy_state,
                'sequence': len(self.l10n_sg_peppol_order_tx_ids),
            }
        )

    def action_send_order_balance(self):
        order_xml = self.env[
            'purchase.edi.xml.ubl_bis3_order_balance'
        ].build_order_balance_xml(self)

        attachment = self.env['ir.attachment'].create(
            {
                'name': f'{self.name}-ubl_bis3_order_balance.xml',
                'raw': order_xml,
                'type': 'binary',
                'mimetype': 'application/xml',
                'res_model': 'purchase.order',
                'res_id': self.id,
            }
        )
        try:
            message_uuid = self._l10n_sg_peppol_send_document(
                filename=attachment.name,
                xml_bytes=order_xml,
            )
            self.message_post(
                body=_('Order balance sent via Peppol.'), attachment_ids=[attachment.id]
            )
            proxy_state = 'processing' if message_uuid != 'test-skip' else 'skipped'
        except (AccountEdiProxyError, UserError) as e:
            message_uuid = False
            proxy_state = 'error'
            error_msg = e.message if isinstance(e, AccountEdiProxyError) else str(e)
            self.message_post(
                body=self.env._(
                    'Failed to send order balance via Peppol: %s',
                    error_msg,
                ),
                attachment_ids=[attachment.id],
            )

        self.env['purchase.peppol.advanced.order.transaction'].create(
            {
                'order_id': self.id,
                'attachment_id': attachment.id,
                'state': 'sent',
                'document_type': 'order_balance',
                'peppol_message_uuid': message_uuid,
                'peppol_proxy_state': proxy_state,
                'sequence': 0,
            }
        )
