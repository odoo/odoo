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
        const line = this.pos.get_order().selected_paymentline;
        const order = this.pos.selectedOrder;
        let retry = localStorage.getItem(order.uid);
        if (!retry) {
            retry = 0;
            localStorage.setItem(order.uid, retry);
        }
        let orderId = order.name.replace(' ','').replaceAll('-','').toUpperCase();
        if (retry > 0) {
            orderId = orderId + 'retry' + retry;
        }
        const transactionAmount = line.amount*100;
        const timeStamp = Math.floor(Date.now() / 1000);
        const response = await this.makePaymentRequest(transactionAmount, orderId, timeStamp);
        if (!response || response['body']['resultInfo']['resultCode'] === "F") {
            let errorMessage = "Unable to establish connection with PayTM";
            if (response) {
                errorMessage = response['body']['resultInfo']['resultMsg'];
            }
            this._showError(errorMessage);
            line.set_payment_status('force_done');
            this._incrementRetry(order.uid);
            throw false;
        }
        line.set_payment_status('waitingCard');
        const pollresponse = await this.pollPayment(orderId, timeStamp);
        if (pollresponse) {
            localStorage.removeItem(order.uid);
            return true;
        }
        else {
            this._incrementRetry(order.uid);
            return false;
        }
    },

    send_payment_cancel: async function (order, cid) {
        this._super.apply(this, arguments);
        const line = this.pos.get_order().selected_paymentline;
        line.set_payment_status('retry');
        this._incrementRetry(order.uid);
        clearTimeout(this.pollTimeout);
        return true;
    },

    pollPayment: async function (transaction, timestamp) {
        const fetchPaymentStatus = async (resolve, reject) => {
            const line = this.pos.get_order().selected_paymentline;
            if (!line || line.payment_status == 'retry') {
                return false;
            }
            try {
                const data = await rpc.query({
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
            } catch {
                const order = this.pos.selectedOrder;
                this._incrementRetry(order.uid);
                line.set_payment_status('force_done');
                this._showError('Unable to establish connection with PayTM API');
                throw false;
            };
        };
        return new Promise(fetchPaymentStatus);
    },

    makePaymentRequest: async function (amount, transaction, timestamp) {
        try {
            const data = await rpc.query({
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
        } catch {
            this._showError('Unable to establish connection with PayTM API');
            throw false;
        };
    },

    // private methods

    _incrementRetry: function (uid) {
        let retry = localStorage.getItem(uid);
        retry++;
        localStorage.setItem(uid, retry);
    },

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
