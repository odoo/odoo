odoo.define('pos_adyen.payment', function (require) {
"use strict";

var core = require('web.core');
var rpc = require('web.rpc');
var { PaymentInterface, registerImplementation } = require('point_of_sale.PaymentInterface');

var _t = core._t;

var PaymentAdyen = PaymentInterface.extend({
    send_payment_request: function (paymentId) {
        this._super.apply(this, arguments);
        this._reset_state();
        const payment = this.model.getRecord('pos.payment', paymentId);
        return this._adyen_pay(payment);
    },
    send_payment_cancel: function (order, paymentId) {
        this._super.apply(this, arguments);
        // set only if we are polling
        this.was_cancelled = !!this.polling;
        const payment = this.model.getRecord('pos.payment', paymentId);
        return this._adyen_cancel(payment);
    },
    close: function () {
        this._super.apply(this, arguments);
    },

    // private methods
    _reset_state: function () {
        this.was_cancelled = false;
        this.last_diagnosis_service_id = false;
        this.remaining_polls = 2;
        clearTimeout(this.polling);
    },

    /**
     * @param {'pos.payment'} payment
     * @param {object} data
     * @returns always rejects
     */
    _handle_odoo_connection_failure: function (payment, data) {
        // handle timeout
        if (payment) {
            this._setPaymentStatus(payment, 'retry');
        }
        this._show_error(_('Could not connect to the Odoo server, please check your internet connection and try again.'));

        return Promise.reject(data); // prevent subsequent onFullFilled's from being called
    },

    _call_adyen: function (payment, data, operation) {
        return rpc.query({
            model: 'pos.payment.method',
            method: 'proxy_adyen_request',
            args: [[this.payment_method.id], data, operation],
        }, {
            // When a payment terminal is disconnected it takes Adyen
            // a while to return an error (~6s). So wait 10 seconds
            // before concluding Odoo is unreachable.
            timeout: 10000,
            shadow: true,
        }).catch(this._handle_odoo_connection_failure.bind(this, payment));
    },

    _adyen_get_sale_id: function () {
        var config = this.model.config;
        return _.str.sprintf('%s (ID: %s)', config.display_name, config.id);
    },

    _adyen_common_message_header: function () {
        this.most_recent_service_id = Math.floor(Math.random() * Math.pow(2, 64)).toString(); // random ID to identify request/response pairs
        this.most_recent_service_id = this.most_recent_service_id.substring(0, 10); // max length is 10

        return {
            'ProtocolVersion': '3.0',
            'MessageClass': 'Service',
            'MessageType': 'Request',
            'SaleID': this._adyen_get_sale_id(),
            'ServiceID': this.most_recent_service_id,
            'POIID': this.payment_method.adyen_terminal_identifier
        };
    },

    _adyen_pay_data: function (payment) {
        var order = this.model.getRecord('pos.order', payment.pos_order_id);
        var config = this.model.config;
        var data = {
            'SaleToPOIRequest': {
                'MessageHeader': _.extend(this._adyen_common_message_header(), {
                    'MessageCategory': 'Payment',
                }),
                'PaymentRequest': {
                    'SaleData': {
                        'SaleTransactionID': {
                            'TransactionID': order.id,
                            'TimeStamp': moment().format(), // iso format: '2018-01-10T11:30:15+00:00'
                        }
                    },
                    'PaymentTransaction': {
                        'AmountsReq': {
                            'Currency': this.model.currency.name,
                            'RequestedAmount': payment.amount,
                        }
                    }
                }
            }
        };

        if (config.adyen_ask_customer_for_tip) {
            data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData = "tenderOption=AskGratuity";
        }

        return data;
    },

    _adyen_pay: async function (payment) {
        if (payment.amount < 0) {
            this._show_error(_('Cannot process transactions with negative amount.'));
            return;
        }
        const data = this._adyen_pay_data(payment);
        const callResult = await this._call_adyen(payment, data);
        return this._adyen_handle_response(payment, data, callResult);
    },

    _adyen_cancel: async function (payment, ignore_error) {
        var previous_service_id = this.most_recent_service_id;
        var header = _.extend(this._adyen_common_message_header(), {
            'MessageCategory': 'Abort',
        });

        var data = {
            'SaleToPOIRequest': {
                'MessageHeader': header,
                'AbortRequest': {
                    'AbortReason': 'MerchantAbort',
                    'MessageReference': {
                        'MessageCategory': 'Payment',
                        'ServiceID': previous_service_id,
                    }
                },
            }
        };

        const callResult = await this._call_adyen(payment, data);
        // Only valid response is a 200 OK HTTP response which is
        // represented by true.
        if (!ignore_error && callResult !== true) {
            this._show_error(_('Cancelling the payment failed. Please cancel it manually on the payment terminal.'));
        }
    },

    _convert_receipt_info: function (output_text) {
        return output_text.reduce(function (acc, entry) {
            var params = new URLSearchParams(entry.Text);

            if (params.get('name') && !params.get('value')) {
                return acc + _.str.sprintf('<br/>%s', params.get('name'));
            } else if (params.get('name') && params.get('value')) {
                return acc + _.str.sprintf('<br/>%s: %s', params.get('name'), params.get('value'));
            }

            return acc;
        }, '');
    },

    _poll_for_response: async function (payment, data, resolve, reject) {
        if (this.was_cancelled) {
            return resolve(false);
        }
        try {
            const status = await rpc.query({
                model: 'pos.payment.method',
                method: 'get_latest_adyen_status',
                args: [[this.payment_method.id], this._adyen_get_sale_id()],
            }, {
                timeout: 5000,
                shadow: true,
            });
            var notification = status.latest_response;
            var last_diagnosis_service_id = status.last_received_diagnosis_id;
            var order = this.model.getRecord('pos.order', payment.pos_order_id);

            if (this.last_diagnosis_service_id != last_diagnosis_service_id) {
                this.last_diagnosis_service_id = last_diagnosis_service_id;
                this.remaining_polls = 2;
            } else {
                this.remaining_polls--;
            }

            if (notification && notification.SaleToPOIResponse.MessageHeader.ServiceID == this.most_recent_service_id) {
                var response = notification.SaleToPOIResponse.PaymentResponse.Response;
                var additional_response = new URLSearchParams(response.AdditionalResponse);

                if (response.Result == 'Success') {
                    var payment_response = notification.SaleToPOIResponse.PaymentResponse;
                    var payment_result = payment_response.PaymentResult;

                    var cashier_receipt = payment_response.PaymentReceipt.find(function (receipt) {
                        return receipt.DocumentQualifier == 'CashierReceipt';
                    });

                    if (cashier_receipt) {
                        await this.model._actionHandler({
                            name: 'actionUpdatePayment',
                            args: [
                                payment,
                                {
                                    cashier_receipt: this._convert_receipt_info(
                                        cashier_receipt.OutputContent.OutputText
                                    ),
                                },
                            ],
                        });
                    }

                    var customer_receipt = payment_response.PaymentReceipt.find(function (receipt) {
                        return receipt.DocumentQualifier == 'CustomerReceipt';
                    });

                    if (customer_receipt) {
                        await this.model._actionHandler({
                            name: 'actionSetReceiptInfo',
                            args: [payment, this._convert_receipt_info(customer_receipt.OutputContent.OutputText)],
                        });
                    }

                    var tip_amount = payment_result.AmountsResp.TipAmount;
                    if (this.model.config.adyen_ask_customer_for_tip && tip_amount > 0) {
                        await this.model._setTip(order, tip_amount);
                        await this.model._actionHandler({
                            name: 'actionUpdatePayment',
                            args: [payment, { amount: payment_result.AmountsResp.AuthorizedAmount }],
                        });
                    }

                    payment.transaction_id = additional_response.get('pspReference');
                    payment.card_type = additional_response.get('cardType');
                    payment.cardholder_name = additional_response.get('cardHolderName') || '';
                    resolve(true);
                } else {
                    var message = additional_response.get('message');
                    this._show_error(_.str.sprintf(_t('Message from Adyen: %s'), message));

                    // this means the transaction was cancelled by pressing the cancel button on the device
                    if (message.startsWith('108 ')) {
                        resolve(false);
                    } else {
                        await this._setPaymentStatus(payment, 'retry');
                        reject();
                    }
                }
            } else if (this.remaining_polls <= 0) {
                this._show_error(_t('The connection to your payment terminal failed. Please check if it is still connected to the internet.'));
                this._adyen_cancel(payment);
                resolve(false);
            }
        } catch (error) {
            this._handle_odoo_connection_failure(payment, data);
            reject(error);
            return;
        }
    },

    _adyen_handle_response: async function (payment, data, response) {
        if (response.error && response.error.status_code == 401) {
            this._show_error(_t('Authentication failed. Please check your Adyen credentials.'));
            await this._setPaymentStatus(payment, 'force_done');
            return;
        }

        response = response.SaleToPOIRequest;
        if (response && response.EventNotification && response.EventNotification.EventToNotify == 'Reject') {
            console.error('error from Adyen', response);

            var msg = '';
            if (response.EventNotification) {
                var params = new URLSearchParams(response.EventNotification.EventDetails);
                msg = params.get('message');
            }

            this._show_error(_.str.sprintf(_t('An unexpected error occured. Message from Adyen: %s'), msg));
            if (payment) {
                await this._setPaymentStatus(payment, 'force_done');
            }
            return;
        } else {
            await this._setPaymentStatus(payment, 'waitingCard');

            var self = this;
            var res = new Promise(function (resolve, reject) {
                // clear previous intervals just in case, otherwise
                // it'll run forever
                clearTimeout(self.polling);

                self.polling = setInterval(function () {
                    self._poll_for_response(payment, data, resolve, reject);
                }, 3000);
            });

            // make sure to stop polling when we're done
            res.finally(function () {
                self._reset_state();
            });

            return res;
        }
    },

    _show_error: function (msg, title) {
        if (!title) {
            title =  _t('Adyen Error');
        }
        this.model.ui.askUser('ErrorPopup',{
            'title': title,
            'body': msg,
        });
    },

    async _setPaymentStatus(payment, status) {
        await this.model._actionHandler({ name: 'actionSetPaymentStatus', args: [payment, status] });
    },
    async _setPaymentTicket(payment, ticket) {
        await this.model._actionHandler({ name: 'actionUpdatePayment', args: [payment, { ticket }] });
    },
});

registerImplementation('adyen', PaymentAdyen);
registerImplementation('odoo_adyen', PaymentAdyen);

return PaymentAdyen;
});
