# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, redirect_with_hash
import logging
import qrcode
from io import BytesIO
import base64
import json
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class WeChatPay(http.Controller):

    def make_qrcode(self, qrurl):
        """generate qrcode from url"""
        img = qrcode.make(qrurl)
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        heximage = base64.b64encode(buffer.getvalue())
        return "data:image/png;base64,{}".format(heximage.decode('utf-8'))

    @http.route('/shop/wechatpay', type='http', auth="public", website=True)
    def index(self, **kw):
        # 获取微信支付
        acquirer = request.env['payment.acquirer'].sudo().search(
            [('provider', '=', 'wechatpay')], limit=1)
        res, data = acquirer._get_qrcode_url(kw)
        values = {}
        if res:
            values['qrcode'] = self.make_qrcode(data)
            values['order'] = kw['reference']
            values['amount'] = kw['amount']
        else:
            values['error'] = data
        return request.render("payment_wechatpay.wechatpay_pay", values)

    @http.route('/shop/wechatpay/result', type='http', auth="public", website=True)
    def wechatpay_query(self, order):
        """query payment result from page"""
        # order = request.website.sale_get_order()
        # 获取微信支付
        acquirer = request.env['payment.acquirer'].sudo().search(
            [('provider', '=', 'wechatpay')], limit=1)
        if acquirer.wechatpy_query_pay(order):
            # 支付成功
            return json.dumps({"result": 0, "order": order})
        return json.dumps({"result": 1, "order": order})

    def validate_pay_data(self, **kwargs):
        res = request.env['payment.transaction'].sudo(
        ).form_feedback(kwargs, 'wechatpay')
        return res

    @http.route('/payment/wechatpay/validate', type="http", auth="none", methods=['POST', 'GET'], csrf=False)
    def wechatpay_validate(self, **kwargs):
        """validate payment result"""
        _logger.info(_("validating payment result..."))
        try:
            res = self.validate_pay_data(**kwargs)
        except ValidationError:
            _logger.exception(_("payment validate failed"))
        return redirect_with_hash("/payment/process")

    @http.route('/payment/wechatpay/notify', csrf=False, type="http", auth='none', method=["POST"])
    def wechatpay_notify(self, **kwargs):
        """receive message from wechatpay server"""
        _logger.debug("Receive data from wechatpay server:{}".format(request.httprequest.data))
        payment = request.env["payment.acquirer"].sudo().search(
            [('provider', '=', 'wechatpay')], limit=1)

        if payment._verify_wechatpay(request.httprequest.data):
            _logger.debug("reply wechatpay server")
            return b"""<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>"""
