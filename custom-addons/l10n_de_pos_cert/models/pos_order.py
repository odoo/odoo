# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


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

    @api.model
    def _order_fields(self, ui_order):
        fields = super()._order_fields(ui_order)
        if self.env.company.l10n_de_is_germany_and_fiskaly() and ui_order.get('fiskaly_uuid'):
            fields['l10n_de_fiskaly_transaction_uuid'] = ui_order['fiskaly_uuid']
            if 'tss_info' in ui_order:
                for key, value in ui_order['tss_info'].items():
                    if value:
                        fields['l10n_de_fiskaly_'+key] = value
        return fields

    def _export_for_ui(self, order):
        json = super()._export_for_ui(order)
        if self.env.company.is_country_germany:
            tss_info = {
                'transaction_number': order.l10n_de_fiskaly_transaction_number,
                'time_start': order.l10n_de_fiskaly_time_start,
                'time_end': order.l10n_de_fiskaly_time_end,
                'certificate_serial': order.l10n_de_fiskaly_certificate_serial,
                'timestamp_format': order.l10n_de_fiskaly_timestamp_format,
                'signature_value': order.l10n_de_fiskaly_signature_value,
                'signature_algorithm': order.l10n_de_fiskaly_signature_algorithm,
                'signature_public_key': order.l10n_de_fiskaly_signature_public_key,
                'client_serial_number': order.l10n_de_fiskaly_client_serial_number
            }
            json['tss_info'] = tss_info
        return json

    def _l10n_de_payment_types(self):
        """
        Used to retrieve a list of information used in the dsfinvk export json template
        :return: [{type[int], amount[int]}]
        """
        self.env.cr.execute("""
            SELECT pm.is_cash_count, sum(p.amount) AS amount
            FROM pos_payment p
                LEFT JOIN pos_payment_method pm ON p.payment_method_id=pm.id
                JOIN account_journal journal ON pm.journal_id=journal.id
            WHERE p.pos_order_id=%s AND journal.type in ('cash', 'bank')
            GROUP BY pm.is_cash_count 
        """, [self.id])

        result = self.env.cr.dictfetchall()
        for payment in result:
            payment['type'] = 'Bar' if payment['is_cash_count'] else 'Unbar'

        return result

    def _l10n_de_amounts_per_vat(self):
        """
        Used to retrieve a list of information of information for the amounts_per_vat key in the dsfinvk json template
        :return: [{amount[int], excl_vat[float], incl_vat[float]}]
        """
        self.env.cr.execute("""
            SELECT account_tax.amount, 
                   sum(pos_order_line.price_subtotal) as excl_vat, 
                   sum(pos_order_line.price_subtotal_incl) as incl_vat 
            FROM pos_order 
            JOIN pos_order_line ON pos_order.id=pos_order_line.order_id 
            JOIN account_tax_pos_order_line_rel ON account_tax_pos_order_line_rel.pos_order_line_id=pos_order_line.id 
            JOIN account_tax ON account_tax_pos_order_line_rel.account_tax_id=account_tax.id
            WHERE pos_order.id=%s 
            GROUP BY account_tax.amount
        """, [self.id])
        return self.env.cr.dictfetchall()

    def refund(self):
        for order in self:
            if order.config_id.l10n_de_fiskaly_tss_id:
                raise UserError(_("You can only refund a customer from the POS Cashier interface"))
        return super().refund()
