# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import formatLang


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_es_invoice_type = fields.Selection(
        selection='_l10n_es_refund_reason_selection',
        string="Refund Reason",
        help="BOE-A-1992-28740. Law 37/1992, of 28 December, on Value Added Tax. Article "
             "80. Modification of the taxable base.",
        copy=False,
    )

    l10n_es_pos_refund_sequence_number = fields.Integer(
        string="Simplified Credit Note Number",
        readonly=True,
        copy=False,
    )

    @api.model
    def _l10n_es_refund_reason_selection(self):
        return self.env['account.move']._l10n_es_refund_reason_selection()

    @api.model
    def _l10n_es_pos_get_refund_reasons(self):
        """Return the refund reasons in the format expected by the POS frontend.

        The selection of `l10n_es_invoice_type` is dynamic, so it has no
        `ir.model.fields.selection` records: it must be resolved through the field
        itself instead of `selection_ids`.

        :return: list of {'value': code, 'name': translated label}
        """
        selection = self._fields['l10n_es_invoice_type']._description_selection(self.env)
        return [{'value': value, 'name': name} for value, name in selection]

    def _l10n_es_pos_get_simplified_invoice_name(self):
        """Return the number of the simplified invoice of this order."""
        self.ensure_one()
        if self.l10n_es_pos_refund_sequence_number:
            return f"R{str(self.config_id.id).zfill(2)}/{str(self.l10n_es_pos_refund_sequence_number).zfill(6)}"
        return f"{self.config_id.id}/{str(self.sequence_number).zfill(6)}"

    def _l10n_es_pos_get_invoice_name(self):
        """Return the number of the fiscal document of this order, as shown on its receipt.
        An order with its own invoice shows the number of that invoice, also when a simplified
        invoice was issued first and invoiced later on: the invoice replaces it (Veri*Factu even
        cancels its record). `is_singly_invoiced` is used instead of `account_move`, which points
        to the session closing entry once the session is closed. Otherwise, the order shows the
        number it got in the series of simplified invoices when it was paid.
        :return: the number, or '' when the order has none yet (e.g. a draft)
        """
        self.ensure_one()
        if self.is_singly_invoiced:
            return self.account_move.name
        if self.sequence_number or self.l10n_es_pos_refund_sequence_number:
            return self._l10n_es_pos_get_simplified_invoice_name()
        return ''

    def _process_saved_order(self, draft):
        # EXTENDS 'point_of_sale'
        self.ensure_one()
        # Only orders being paid: drafts (e.g. open restaurant tables) are not issued yet,
        # whether they will be invoiced is only known at payment.
        if not draft and self.state != 'cancel':
            self._l10n_es_pos_check_simplified_invoice_limit()
        return super()._process_saved_order(draft)

    def _l10n_es_pos_check_simplified_invoice_limit(self):
        """Prevent issuing a simplified invoice above the legal limit of the company.

        The amount equal to the limit is allowed: a simplified invoice can be issued
        when the amount does not exceed it.
        """
        self.ensure_one()
        if not self.company_id._l10n_es_pos_get_fiscal_mode() or self.to_invoice:
            return
        limit = self.company_id.l10n_es_simplified_invoice_limit
        if self.currency_id.compare_amounts(self.amount_total, limit) > 0:
            raise UserError(_(
                "The order needs to be invoiced since its total amount is above %s.",
                formatLang(self.env, limit, currency_obj=self.company_id.currency_id),
            ))

    def action_pos_order_paid(self):
        # EXTENDS 'point_of_sale'
        # Called both when the order is paid from the POS and from the backend payment wizard.
        # The EDI modules extend it too and generate their document after their `super()`,
        # so the number is already set when they read it.
        res = super().action_pos_order_paid()
        self._l10n_es_pos_assign_simplified_invoice_number()
        return res

    def _l10n_es_pos_assign_simplified_invoice_number(self):
        """Number the order in the series of simplified invoices, once it is paid.

        The number is taken at payment instead of at creation: an order created as a draft
        (e.g. an open restaurant table) may still be cancelled or invoiced, and would leave
        a gap in the series. Orders paid to be invoiced keep `sequence_number` = 0, as they
        get an invoice number instead.
        """
        self.ensure_one()
        if (
            not self.company_id._l10n_es_pos_get_fiscal_mode()
            or self.to_invoice
            or self.sequence_number
            or self.l10n_es_pos_refund_sequence_number
        ):
            return
        if self.refunded_order_id:
            self.l10n_es_pos_refund_sequence_number = int(
                self.config_id.l10n_es_pos_refund_sequence_id.sudo().next_by_id()
            )
            return
        values = {}
        super()._update_sequence_number(self.session_id, values)
        self.sequence_number = values['sequence_number']

    def _update_sequence_number(self, session, values):
        # EXTENDS 'point_of_sale'
        # Called at the creation of every order. With a fiscal mode, the number is only
        # assigned at payment: see `_l10n_es_pos_assign_simplified_invoice_number`.
        if session.config_id.company_id._l10n_es_pos_get_fiscal_mode():
            return
        super()._update_sequence_number(session, values)

    def test_invoiced_refund_takes_no_number(self):
        """ A refund paid to be invoiced gets an invoice number: no simplified credit note number.
        All the refunds are invoiced with SII, and the refunds of invoiced orders with TicketBAI
        and Veri*Factu. """
        self.open_new_session(0.0)
        order = self._create_sale(is_invoiced=True, customer=self.partner_b)
        refund = self.env['pos.order'].browse(order.refund()['res_id'])
        refund.to_invoice = True
        self.make_payment(refund, self.bank_pm1, refund.amount_total)

        self.assertTrue(refund.is_singly_invoiced)
        self.assertFalse(refund.sequence_number)
        self.assertFalse(refund.l10n_es_pos_refund_sequence_number)
        self.assertEqual(refund._l10n_es_pos_get_invoice_name(), refund.account_move.name)
