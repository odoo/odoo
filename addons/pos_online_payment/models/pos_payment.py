# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    online_account_payment_id = fields.Many2one('account.payment', string='Online accounting payment', readonly=True) # One2one

    @api.model_create_multi
    def create(self, vals_list):
        online_account_payments_by_pm = {}
        for vals in vals_list:
            pm_id = vals['payment_method_id']
            if pm_id not in online_account_payments_by_pm:
                online_account_payments_by_pm[pm_id] = set()
            if vals.get('online_account_payment_id'):
                online_account_payments_by_pm[pm_id].add(vals['online_account_payment_id'])

        opms_read_id = self.env['pos.payment.method'].search_read(['&', ('id', 'in', list(online_account_payments_by_pm.keys())), ('is_online_payment', '=', True)], ["id"])
        opms_id = {opm_read_id['id'] for opm_read_id in opms_read_id}
        online_account_payments_to_check_id = set()

        for pm_id, oaps_id in online_account_payments_by_pm.items():
            if pm_id in opms_id:
                if None in oaps_id:
                    raise UserError(_("Cannot create a POS online payment without an accounting payment."))
                else:
                    online_account_payments_to_check_id.update(oaps_id)
            elif any(oaps_id):
                raise UserError(_("Cannot create a POS payment with a not online payment method and an online accounting payment."))

        if online_account_payments_to_check_id:
            valid_oap_amount = self.env['account.payment'].search_count([('id', 'in', list(online_account_payments_to_check_id))])
            if valid_oap_amount != len(online_account_payments_to_check_id):
                raise UserError(_("Cannot create a POS online payment without an accounting payment."))

        return super().create(vals_list)

    def write(self, vals):
        if vals.keys() & ('amount', 'payment_date', 'payment_method_id', 'online_account_payment_id', 'pos_order_id') and any(payment.online_account_payment_id or payment.payment_method_id.is_online_payment for payment in self):
            raise UserError(_("Cannot edit a POS online payment essential data."))
        return super().write(vals)

    @api.constrains('payment_method_id')
    def _check_payment_method_id(self):
        bypass_check_payments = self.filtered(lambda rec: rec.payment_method_id.is_online_payment)
        if any(payment.payment_method_id != payment.pos_order_id.online_payment_method_id for payment in bypass_check_payments):
            # An online payment must always be saved for the POS, even if the online payment method is no longer configured/allowed in the pos.config, because in any case it is saved by account_payment and payment modules.
            _logger.warning("Allow to save a POS online payment with an unexpected online payment method")

        super(PosPayment, self - bypass_check_payments)._check_payment_method_id()
