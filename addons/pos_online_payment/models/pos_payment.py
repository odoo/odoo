# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    online_account_payment_id = fields.Many2one('account.payment', string='Online accounting payment', readonly=True)  # One2one

    @api.model_create_multi
    def create(self, vals_list):
        online_account_payments_by_pm = {}
        for vals in vals_list:
            pm_id = vals['payment_method_id']
            if pm_id not in online_account_payments_by_pm:
                online_account_payments_by_pm[pm_id] = set()
            online_account_payments_by_pm[pm_id].add(vals.get('online_account_payment_id') or None)

        opms_read_id = self.env['pos.payment.method'].search_fetch(['&', ('id', 'in', list(online_account_payments_by_pm.keys())), ('type', '=', 'online')], ["id"])
        opms_id = {opm_read_id.id for opm_read_id in opms_read_id}
        online_account_payments_to_check_id = set()

        for vals in vals_list:
            if vals.get('online_account_payment_id') and not self.env.context.get('pos_online_payment_from_tx'):
                raise UserError(_("Only an online payment transaction can set the accounting payment of a POS payment."))
            if vals['payment_method_id'] in opms_id and not vals.get('online_account_payment_id') and vals.get('payment_status') in (None, False, 'done'):
                raise UserError(_("Cannot create a POS online payment without an accounting payment."))

        for pm_id, oaps_id in online_account_payments_by_pm.items():
            if pm_id in opms_id:
                online_account_payments_to_check_id.update(oaps_id - {None})
            elif any(oaps_id):
                raise UserError(_("Cannot create a POS payment with a not online payment method and an online accounting payment."))

        if online_account_payments_to_check_id:
            valid_oap_amount = self.env['account.payment'].search_count([('id', 'in', list(online_account_payments_to_check_id))])
            if valid_oap_amount != len(online_account_payments_to_check_id):
                raise UserError(_("Cannot create a POS online payment without an accounting payment."))

        return super().create(vals_list)

    def write(self, vals):
        if 'online_account_payment_id' in vals and not self.env.context.get('pos_online_payment_from_tx'):
            raise UserError(_("Only an online payment transaction can set the accounting payment of a POS payment."))
        if 'payment_status' in vals and vals['payment_status'] in (None, False, 'done') and not vals.get('online_account_payment_id') and any(payment.payment_method_id.type == 'online' and not payment.online_account_payment_id for payment in self):
            raise UserError(_("Cannot mark a POS online payment as paid without an accounting payment."))
        if 'payment_method_id' in vals and any(payment.payment_method_id.type == 'online' and payment.payment_method_id.id != vals['payment_method_id'] for payment in self):
            raise UserError(_("Cannot edit a POS online payment essential data."))
        paid_payments = self.filtered('online_account_payment_id')
        protected_fields = vals.keys() & self._get_online_payment_protected_fields()
        if paid_payments and protected_fields:
            res = super(PosPayment, self - paid_payments).write(vals)
            return super(PosPayment, paid_payments).write({key: value for key, value in vals.items() if key not in protected_fields}) and res
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_paid_online_payment(self):
        if any(payment.online_account_payment_id for payment in self):
            raise UserError(_("Cannot delete a paid POS online payment."))

    @api.model
    def _get_online_payment_protected_fields(self):
        return {
            'amount', 'amount_currency', 'foreign_currency_id', 'payment_date', 'online_account_payment_id',
            'pos_order_id', 'payment_status', 'is_change',
        }

    @api.constrains('payment_method_id')
    def _check_payment_method_id(self):
        bypass_check_payments = self.filtered(lambda p: p.payment_method_id.type == 'online')
        if any(payment.payment_method_id != payment.pos_order_id.online_payment_method_id for payment in bypass_check_payments):
            # An online payment must always be saved for the POS, even if the online payment method is no longer configured/allowed in the pos.config, because in any case it is saved by account_payment and payment modules.
            _logger.warning("Allow to save a POS online payment with an unexpected online payment method")

        super(PosPayment, self - bypass_check_payments)._check_payment_method_id()
