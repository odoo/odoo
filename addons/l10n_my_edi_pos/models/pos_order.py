# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    # ------------------
    # Fields declaration
    # ------------------

    consolidated_invoice_ids = fields.Many2many(
        name="Consolidated Invoices",
        comodel_name="myinvois.document",
        relation="myinvois_document_pos_order_rel",
        column1="order_id",
        column2="document_id",
        groups="account.group_account_invoice",
    )

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def _process_order(self, order, existing_order):
        """ There are a few cases where we want to block the creation of the order to maintain correct data for the EDI. """
        # Start by looking in the data to see if we have any refund lines; and if so we want to gather all refunded orders.
        session = self.env['pos.session'].browse(order['session_id'])
        if not session.config_id.company_id._l10n_my_edi_enabled():
            return super()._process_order(order, existing_order)

        refunded_order_line_ids = []
        for line in order['lines']:
            line_data = line[-1]
            if not line_data.get('refunded_orderline_id'):
                continue
            refunded_order_line_ids.append(line_data['refunded_orderline_id'])

        refunded_orders = self.env['pos.order.line'].browse(refunded_order_line_ids).order_id
        if not refunded_orders:  # Nothing more to do for now.
            return super()._process_order(order, existing_order)

        # If the order contains refund lines, we need to assert that we invoice (or not) the order based on the state of
        # the orders being refunded.
        to_invoice = order.get('to_invoice')

        for refunded_order in refunded_orders:
            submitted = ((refunded_order.is_invoiced and refunded_order.account_move.l10n_my_edi_state in ["in_progress", "valid", "rejected"])
                         or (refunded_order._get_active_consolidated_invoice() and refunded_order._get_active_consolidated_invoice().myinvois_state in ["in_progress", "valid", "rejected"]))

            if submitted and not to_invoice:
                raise UserError(refunded_order.env._('You must invoice a refund for an order that has been submitted to MyInvois.'))
            if not submitted and to_invoice:
                raise UserError(refunded_order.env._('You cannot invoice a refund for an order that has not been submitted to MyInvois yet.'))

            if refunded_order._get_active_consolidated_invoice():
                if not to_invoice:
                    # When we refund an order which is included in a not-yet-sent consolidated invoice, we link the refund to it.
                    order['consolidated_invoice_ids'] = refunded_order._get_active_consolidated_invoice().id

        return super()._process_order(order, existing_order)

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super()._order_fields(ui_order)
        if ui_order.get('consolidated_invoice_ids'):
            order_fields['consolidated_invoice_ids'] = [Command.link(ui_order['consolidated_invoice_ids'])]
        return order_fields

    @api.model
    def _generate_pos_order_invoice(self):
        # EXTENDS 'point_of_sale'
        if self.company_id._l10n_my_edi_enabled():
            for order in self:
                if order._get_active_consolidated_invoice():
                    raise UserError(order.env._("This order has been included in a consolidated invoice and cannot be invoiced separately."))

                refunded_consolidated_invoice = order.refunded_order_id and order.refunded_order_id._get_active_consolidated_invoice()
                refunding_consolidated_invoice = refunded_consolidated_invoice and refunded_consolidated_invoice.myinvois_state in ["in_progress", "valid", "rejected"]
                # We can skip this check when refunding a consolidated invoice, since the customer in the XML is fixed.
                if not refunding_consolidated_invoice:
                    partner = order.partner_id
                    if (
                        not partner.l10n_my_identification_type
                        or not partner.l10n_my_identification_number
                    ):
                        raise UserError(order.env._("You must set the identification information on the commercial partner."))
                    if not partner._l10n_my_edi_get_tin_for_myinvois():
                        raise UserError(order.env._("You must set a TIN number on the commercial partner."))

            # We need to wait for MyInvois to give us a code during submission before generating the PDF file.
            # To do so, we will invoice without PDF, send and only then generate the PDF file.
            action_values = super(PosOrder, self.with_context(generate_pdf=False))._generate_pos_order_invoice()

            # At this point we don't want to raise anymore, if there are issues it'll be logged on the invoice, and we will
            # move on.
            self.account_move.action_l10n_my_edi_send_invoice()

            if self.env.context.get('generate_pdf', True):
                self.account_move.with_context(skip_invoice_sync=True)._generate_and_send()

            return action_values
        return super()._generate_pos_order_invoice()

    # --------------
    # Action methods
    # --------------

    def action_show_myinvois_documents(self):
        return self._get_active_consolidated_invoice().action_show_myinvois_documents()

    # ----------------
    # Business methods
    # ----------------

    def _get_active_consolidated_invoice(self, including_in_progress=False):
        """ Small helper to get the currently active consolidated invoice if more that one is linked to an order. """
        return self.env['myinvois.document'].union(*[order.consolidated_invoice_ids._get_active_myinvois_document(including_in_progress) for order in self])
