# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_repr


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_de_fiskaly_transaction_uuid = fields.Char(string="Transaction ID", readonly=True, copy=False)
    l10n_de_fiskaly_transaction_number = fields.Integer(string="Transaction Number", readonly=True, copy=False)
    l10n_de_fiskaly_time_start = fields.Datetime(string="Beginning", readonly=True, copy=False)
    l10n_de_fiskaly_time_end = fields.Datetime(string="End", readonly=True, copy=False)
    l10n_de_fiskaly_certificate_serial = fields.Char(string="Certificate Serial", readonly=True, copy=False)
    l10n_de_fiskaly_timestamp_format = fields.Char(string="Timestamp Format", readonly=True, copy=False)
    l10n_de_fiskaly_signature_value = fields.Char(string="Signature Value", readonly=True, copy=False)
    l10n_de_fiskaly_signature_algorithm = fields.Char(string="Signature Algo", readonly=True, copy=False)
    l10n_de_fiskaly_signature_public_key = fields.Char(string="Signature Public Key", readonly=True, copy=False)
    l10n_de_fiskaly_client_serial_number = fields.Char(string="Client Serial", readonly=True, copy=False)

    def _prepare_lines_and_payments(self):
        is_adjusted = True  # mostly orders are adjusted
        lines_export_data = []
        payment_data = []
        for i, line in enumerate(self.lines, start=1):
            line_data, adjusted = line.prepare_line_data(is_adjusted, i)
            # Ensure is_adjusted remains False once set; prevent it from overridden by True if was False because of loop
            if not adjusted:
                is_adjusted = False
            lines_export_data.append(line_data)

        payment_data = self._l10n_de_payment_types()
        precision = self.currency_id.decimal_places
        # Add a adjustment line for the orders paid via customer account (receivalble account)
        # This adjustment line offsets the amount and will be shown as payable during settlement
        keine_payment = next((p for p in payment_data if p['type'] == 'Keine'), None)
        if not is_adjusted and keine_payment:
            pm_amount = -float(keine_payment['amount'])  # -ve as this is an adjustment
            # uninvoiced orders handled same as MPGV use, invoiced ones work as specific type.
            type = 'Forderungsentstehung' if self.account_move else 'MehrzweckgutscheinEinloesung'
            lines_export_data.append({
                'business_case': {
                    'type': type,
                    'amounts_per_vat_id': [self.session_id._get_vat_details(5, pm_amount, pm_amount)],
                },
                'lineitem_export_id': str(len(self.lines) + 1),  # It should be unique and start over for each order from 1
                'storno': False,
                'text': _('Adjustment Line'),
                'item': {
                    'number': 'NaN',  # we are not creating any product for adjustment so just send NaN
                    'quantity': 1,
                    'price_per_unit': float_repr(pm_amount, precision),
                },
            })
            # adjust payment lines accordingly
            keine_payment.update({'amount': float_repr(0, precision)})

        return lines_export_data, payment_data

    def _l10n_de_payment_types(self):
        """
        Used to retrieve a list of information for the payment of the order to send in the dsfinvk export json template
        | is_cash_count   | has_journal  | amount | name |
        | --------------- | ------------ | ------ |------|
        | True            | True         |   xx   |      | can be cash pm (Bar)
        | False           | True         |   xx   |      | can be bank, online transactions, etc. (Unbar)
        | False           | False        |   xx   |      | receivable accounts like customer account (Keine)
        :return: [{is_cash_count[bool], has_journal[bool], amount[int], name[str], type[str]}]
        """
        self.env.cr.execute("""
            SELECT pm.is_cash_count,
                journal.id IS NOT NULL AS has_journal,
                SUM(p.amount) AS amount,
                pm.name
            FROM pos_payment p
                LEFT JOIN pos_payment_method pm ON p.payment_method_id=pm.id
                LEFT JOIN account_journal journal ON pm.journal_id=journal.id
            WHERE p.pos_order_id = %s
            GROUP BY pm.is_cash_count, has_journal, pm.name
        """, [self.id])

        result = self.env.cr.dictfetchall()
        only_settlements = False
        if hasattr(self.config_id, 'settle_due_product_id'):
            settlement_products = [self.config_id.settle_due_product_id.id, self.config_id.settle_invoice_product_id.id, self.config_id.deposit_product_id.id]
            # Check if all lines have only deposit or settle due products
            only_settlements = all(line.product_id.id in settlement_products for line in self.lines)

        payment_data = []
        for payment in result:
            payment_type = 'Bar'  # Default
            if not payment['is_cash_count']:
                if payment['has_journal']:
                    payment_type = 'Unbar'
                elif not only_settlements:
                    payment_type = 'Keine'
                else:
                    continue  # Skip 'Keine' for settlement orders as already adjusted to make total null in the order.

            payment_data.append({
                'name': str(payment['name'])[:60],
                'type': payment_type,
                'currency_code': self.currency_id.name or 'EUR',
                'amount': float_repr(payment['amount'], self.currency_id.decimal_places),
            })

        return payment_data

    def _l10n_de_amounts_per_vat(self):
        """
        Used to retrieve a list of information for the amounts_per_vat key in the dsfinvk json template
        :return: [{tax_id[int], excl_vat[float], incl_vat[float]}]
        """
        self.env.cr.execute("""
            SELECT account_tax.id as tax_id,
                   sum(pos_order_line.price_subtotal) as excl_vat, 
                   sum(pos_order_line.price_subtotal_incl) as incl_vat 
            FROM pos_order 
            JOIN pos_order_line ON pos_order.id=pos_order_line.order_id 
            JOIN account_tax_pos_order_line_rel ON account_tax_pos_order_line_rel.pos_order_line_id=pos_order_line.id 
            JOIN account_tax ON account_tax_pos_order_line_rel.account_tax_id=account_tax.id
            WHERE pos_order.id=%s 
            GROUP BY account_tax.id
        """, [self.id])
        datas = self.env.cr.dictfetchall()

        result = []
        for data in datas:
            vat_export_id = self.env['account.tax'].browse(data['tax_id']).get_vat_definition_id() if data['tax_id'] else 5  # no tax -> considered as non taxable
            result.append(self.session_id._get_vat_details(vat_export_id, data['incl_vat'], data['excl_vat']))
        return result

    def refund(self):
        for order in self:
            if order.config_id.l10n_de_fiskaly_tss_id:
                raise UserError(_("You can only refund a customer from the POS Cashier interface"))
        return super().refund()
