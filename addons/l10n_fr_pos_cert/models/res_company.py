# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields, _
from odoo.exceptions import UserError
from datetime import datetime
from odoo.fields import Datetime, Date
from odoo.tools.misc import format_date
import pytz


def ctx_tz(record, field):
    res_lang = None
    ctx = record.env.context
    tz_name = pytz.timezone(ctx.get('tz') or record.env.user.tz or 'UTC')
    timestamp = Datetime.from_string(record[field])
    if ctx.get('lang'):
        res_lang = record.env['res.lang']._get_data(code=ctx['lang'])
    if res_lang:
        timestamp = pytz.utc.localize(timestamp, is_dst=False)
        return datetime.strftime(timestamp.astimezone(tz_name), res_lang.date_format + ' ' + res_lang.time_format)
    return Datetime.context_timestamp(record, timestamp)


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_pos_cert_sequence_id = fields.Many2one('ir.sequence')

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        for company in companies:
            #when creating a new french company, create the securisation sequence as well
            if company._is_accounting_unalterable():
                sequence_fields = ['l10n_fr_pos_cert_sequence_id']
                company._create_secure_sequence(sequence_fields)
        return companies

    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        #if country changed to fr, create the securisation sequence
        for company in self:
            if company._is_accounting_unalterable():
                sequence_fields = ['l10n_fr_pos_cert_sequence_id']
                company._create_secure_sequence(sequence_fields)
        return res

    def _action_check_pos_hash_integrity(self):
        return self.env.ref('l10n_fr_pos_cert.action_report_pos_hash_integrity').report_action(self.id)

    def _check_pos_hash_integrity(self):
        """Checks that all posted or invoiced pos orders have still the same data as when they were posted
        and raises an error with the result.
        """
        def build_order_info(order):
            entry_reference = _('(Receipt ref.: %s)')
            order_reference_string = order.pos_reference and entry_reference % order.pos_reference or ''
            return [ctx_tz(order, 'date_order'), order.l10n_fr_hash, order.name, order_reference_string, ctx_tz(order, 'write_date')]

        msg_alert = ''
        report_dict = {}
        if self._is_accounting_unalterable():
            orders = self.with_context(prefetch_fields=False).env['pos.order'].search([('state', 'in', ['paid', 'done']), ('company_id', '=', self.id),
                                    ('l10n_fr_secure_sequence_number', '!=', 0)], order="l10n_fr_secure_sequence_number ASC")

            if not orders:
                msg_alert = (_('There isn\'t any order flagged for data inalterability yet for the company %s. This mechanism only runs for point of sale orders generated after the installation of the module France - Certification CGI 286 I-3 bis. - POS', self.env.company.name))
                raise UserError(msg_alert)

            previous_hash = u''
            corrupted_orders = []
            for order in orders:
                if order.l10n_fr_hash != order._compute_hash(previous_hash=previous_hash):
                    corrupted_orders.append(order.name)
                    msg_alert = (_('Corrupted data on point of sale order with id %s.', order.id))
                previous_hash = order.l10n_fr_hash
            orders.invalidate_recordset()

            orders_sorted_date = orders.sorted(lambda o: o.date_order)
            start_order_info = build_order_info(orders_sorted_date[0])
            end_order_info = build_order_info(orders_sorted_date[-1])

            report_dict.update({
                'first_order_name': start_order_info[2],
                'first_order_hash': start_order_info[1],
                'first_order_date': start_order_info[0],
                'last_order_name': end_order_info[2],
                'last_order_hash': end_order_info[1],
                'last_order_date': end_order_info[0],
            })
            corrupted_orders = ', '.join([o for o in corrupted_orders])
            return {
                'result': report_dict or 'None',
                'msg_alert': msg_alert or 'None',
                'printing_date': format_date(self.env,  Date.to_string( Date.today())),
                'corrupted_orders': corrupted_orders or 'None'
            }
        else:
            raise UserError(_('Accounting is not unalterable for the company %s. This mechanism is designed for companies where accounting is unalterable.', self.env.company.name))
