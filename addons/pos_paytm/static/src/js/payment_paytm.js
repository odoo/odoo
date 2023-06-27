/* global PaytmTerminal */
odoo.define('pos_paytm.payment', function (require) {
"use strict";

const core = require('web.core');
const rpc = require('web.rpc');
const PaymentInterface = require('point_of_sale.PaymentInterface');
const { Gui } = require('point_of_sale.Gui');

const _t = core._t;

let PaymentPaytm = PaymentInterface.extend({
    init: function (pos, payment_method) {
        this._super(...arguments);
    },

    send_payment_request: async function (cid) {
        /**
         * Override
         */
        this._super.apply(this, arguments);
        let line = this.pos.get_order().selected_paymentline;
        let order = this.pos.selectedOrder;
        let retry = localStorage.getItem(order.uid);
        if (!retry) {
            retry = 0;
            localStorage.setItem(order.uid, retry);
        }
        let orderId = order.name.replace(' ','').replaceAll('-','').toUpperCase();
        if (retry > 0) {
            orderId = orderId + 'retry' + retry;
        }
        let transactionAmount = line.amount*100;
        let timeStamp = Math.floor(Date.now() / 1000);
        let response = await this.makePaymentRequest(transactionAmount, orderId, timeStamp);
        if (response['body']['resultInfo']['resultCode'] === "F") {
            this._showError(response['body']['resultInfo']['resultMsg']);
            line.set_payment_status('force_done');
            retry++;
            localStorage.setItem(order.uid, retry);
            throw false;
        }
        line.set_payment_status('waitingCard');
        let pollresponse = await this.pollPayment(orderId, timeStamp);
        if (pollresponse) {
            localStorage.removeItem(order.uid);
            return true;
        }
        else {
            retry++;
            localStorage.setItem(order.uid, retry);
            return false;
        }
    },

    send_payment_cancel: async function (order, cid) {
        this._super.apply(this, arguments);
        let line = this.pos.get_order().selected_paymentline;
        line.set_payment_status('retry');
        let retry = localStorage.getItem(order.uid);
        clearTimeout(this.pollTimeout);
        retry++;
        localStorage.setItem(order.uid, retry);
        return true;
    },


    pollPayment: async function (transaction, timestamp) {
        const fetchPaymentStatus = async (resolve, reject) => {
            let line = this.pos.get_order().selected_paymentline;
            if (!line || line.payment_status == 'retry') {
                return false;
            }
            try {
                let data = await rpc.query({
                    model: 'pos.payment.method',
                    method: 'paytm_fetch_payment_status',
                    args: [[this.payment_method.id], transaction, timestamp],
                }, {
                    silent: true,
                });
                if (data.error) {
                    throw false;
                }
                let result = data['body']['resultInfo']['resultCode'];
                if (result === "F") {
                    this._showError(data['body']['resultInfo']['resultMsg']);
                    return resolve(false);
                }
                else if (result === 'A' || result === 'S') {
                    return resolve(data);
                }
                else {
                    this.pollTimeout = setTimeout(fetchPaymentStatus, 5000, resolve, reject);
                }
            } catch (error) {
                let order = this.pos.selectedOrder;
                let retry = localStorage.getItem(order.uid);
                retry++;
                localStorage.setItem(order.uid, retry);
                line.set_payment_status('force_done');
                this._showError('Unable to establish connection with PayTM API');
                throw false;
                
            };
        };
        return new Promise(fetchPaymentStatus);
    },

    makePaymentRequest: async function (amount, transaction, timestamp) {
        try {
            let data = await rpc.query({
                model: 'pos.payment.method',
                method: 'paytm_make_payment_request',
                args: [[this.payment_method.id], amount, transaction, timestamp],
            }, {
                silent: true,
            });
            if (data.error) {
                throw data.error;
            }
            return data;
        } catch (error) {
            this._showError('Unable to establish connection with PayTM API');
            return false;
        };
    },

    // private methods

    _showError: function (msg, title) {
        if (!title) {
            title =  _t('PayTM Error');
        }
        Gui.showPopup('ErrorPopup',{
            'title': title,
            'body': msg,
        });
    },
});

return PaymentPaytm;
});
