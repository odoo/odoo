#!/usr/bin/python3
# @Time    : 2019-11-26
# @Author  : Kevin Kong (kfx2007@163.com)

from odoo import models, fields, api, _
from wechatpy.pay import WeChatPay
from odoo.exceptions import ValidationError
import logging
from datetime import datetime, timedelta
from dateutil import tz
import traceback

_logger = logging.getLogger(__name__)


class AcquirerWeChatPay(models.Model):
    _inherit = "payment.acquirer"

    provider = fields.Selection(selection_add=[('wechatpay', 'WeChatPay')],ondelete={'wechatpay':'set default'})
    wechatpay_appid = fields.Char("WeChatPay AppId", size=32)
    wechatpay_app_key = fields.Char("Api Key")
    wechatpay_mch_id = fields.Char("Merchant Id", size=32)
    wechatpay_mch_key = fields.Char("Merchat Key File Path")
    wechatpay_mch_cert = fields.Char("Merchant Cert File Path")

    def _get_feature_support(self):
        res = super(AcquirerWeChatPay, self)._get_feature_support()
        res['fees'].append('wechatpay')
        return res

    def _get_wechatpay(self):
        """get wechatpay client"""
        try:
            # WeChatPay has no sandbox enviroment.
            wechatpay = WeChatPay(self.wechatpay_appid,
                                  self.wechatpay_app_key,
                                  self.wechatpay_mch_id,
                                  mch_cert=self.wechatpay_mch_cert,
                                  mch_key=self.wechatpay_mch_key)
            return wechatpay
        except Exception as err:
            _logger.exception(_(f"generate wechatpay client error:{err}"))

    def _get_qrcode_url(self, kw):
        """get wechatpay qrcode"""
        try:
            base_url = self.env['ir.config_parameter'].sudo(
            ).get_param('web.base.url')
            wechatpay = self._get_wechatpay()
            # 服务器时间为UTC时间，因此需要转换成东八区时间
            tz_sh = tz.gettz("Asia/Shanghai")
            date_start = datetime.now().astimezone(tz_sh)
            date_end = (datetime.now()+timedelta(hours=2)).astimezone(tz_sh)
            amount = int(float(kw['amount']) * 100)
            res = wechatpay.order.create(trade_type="NATIVE", body=kw['reference'], time_start=date_start, time_expire=date_end,
                                         out_trade_no=kw['reference'], total_fee=amount, notify_url="{}{}".format(base_url, '/payment/wechatpay/notify'))
            if res['return_code'] == "SUCCESS":
                # 预生成订单成功
                return True, res['code_url']
            _logger.error(_("wechatpay pre order error：{}".format(res)))
            raise ValidationError(_("wechatpay pre order error"))
        except Exception as err:
            return False, err

    def wechatpay_get_form_action_url(self):
        """union pay"""
        return "/shop/wechatpay"

    @api.model
    def wechatpy_query_pay(self, order):
        """
        using merchat id to get pay status from wechat server.
        only SUCCESS means success, anything else failed.
        """
        wechatpay = self._get_wechatpay()
        res = wechatpay.order.query(out_trade_no=order)
        _logger.info(_("Result form wechatpay server:{}".format(res)))
        if res["return_code"] == "SUCCESS" and res["result_code"] == "SUCCESS":
            if res["trade_state"] == "SUCCESS":
                transaction = self.env["payment.transaction"].sudo().search(
                    [('reference', '=', order)], limit=1)
                if transaction.state in ('draft', 'pending', 'authorized'):
                    # 将支付结果设置完成
                    result = {
                        "acquirer_reference": res['transaction_id']
                    }
                    transaction.write(result)
                    transaction._set_transaction_done()
                    # 完成付款单
                    sale_order = self.env['sale.order'].search(
                        [('name', '=', order)], limit=1)
                    _logger.info("Process payment order {}...".format(order))
                    if sale_order:
                        elect = self.env.ref(
                            'payment.account_payment_method_electronic_in').id
                        sale_order.custom_payment_id.payment_method_id = elect
                        sale_order.custom_payment_id.payment_transaction_id = transaction.id
                        sale_order.custom_payment_id.post()

                    return True
                elif transaction.state == 'done':
                    return True
                else:
                    return False
        return False

    def wechatpay_from_generate_values(self, values):
        wechatpay_tx_values = dict(values)
        return wechatpay_tx_values

    def _verify_wechatpay(self, data):
        """validate results from wechatpay server"""
        try:
            wechatpay = self._get_wechatpay()
            result = wechatpay.parse_payment_result(data)
            _logger.info("Parse result from wechatpay server：{}".format(result))
            if result['result_code'] == 'SUCCESS' and result['return_code'] == 'SUCCESS':
                # 支付校验成功
                transaction = self.env["payment.transaction"].sudo().search(
                    [('reference', '=', result["out_trade_no"])], limit=1)
                if transaction.state in ('draft', 'pending', 'authorized'):
                    # 将支付结果设置完成
                    res = {
                        "acquirer_reference": result['transaction_id']
                    }
                    transaction.write(res)
                    transaction._set_transaction_done()
                    # 完成付款单
                    sale_order = self.env['sale.order'].search(
                        [('name', '=', result["out_trade_no"])], limit=1)
                    _logger.info("handler wechatpay payment order {}...".format(result["out_trade_no"]))
                    if sale_order:
                        elect = self.env.ref(
                            'payment.account_payment_method_electronic_in').id
                        sale_order.custom_payment_id.payment_method_id = elect
                        sale_order.custom_payment_id.payment_transaction_id = transaction.id
                        sale_order.custom_payment_id.post()

                    return True
                elif transaction.state == 'done':
                    return True
                else:
                    return False
            return False
        except Exception as err:
            _logger.error("Parse result from wechatpay error:{}".format(traceback.format_exc()))
            return False


class TxWeChatpay(models.Model):
    _inherit = "payment.transaction"

    wechatpay_txn_type = fields.Char('Transaction type')

    @api.model
    def _wechatpay_form_get_tx_from_data(self, data):
        """get payment transaction"""
        if not data.get("order", None):
            raise ValidationError(_("Wrong order no."))
        reference = data.get("order")
        txs = self.env["payment.transaction"].search(
            [('reference', '=', reference)])
        if not txs or len(txs) > 1:
            error_msg = 'WeChatPay: received data for reference %s' % (
                reference)
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return txs[0]

    def _wechatpay_form_validate(self, data):
        """validate wechatpay"""
        if self.state == 'done':
            _logger.info(f"payment has been confirmed：{data['order']}")
            return True
        # 根据微信支付服务器返回的信息，去微信支付服务器查询
        payment = self.env["payment.acquirer"].sudo().search(
            [('provider', '=', 'wechatpay')], limit=1)
        return payment.wechatpy_query_pay(data['order'])
