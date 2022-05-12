odoo.define('pos_adyen.payment', function (require) {
"use strict";

var core = require('web.core');
var rpc = require('web.rpc');
var PaymentInterface = require('point_of_sale.PaymentInterface');
const { Gui } = require('point_of_sale.Gui');

var _t = core._t;

var PaymentAdyen = PaymentInterface.extend({
    /**
     * Sending an adyen payment request is asynchronous such that this method has to
     * wait for the payment status to arrive. The payment status will originate from
     * adyen server telling the odoo instance about the payment status, then the
     * odoo instance will broadcast the payment status which will eventually be
     * handled here in the UI by calling `handleAsyncPaymentStatus`. For proper orchestration,
     * this method has to return a promise that only resolves when the payment status
     * arrived; thus, we need to set `_paymentRequestResolve` and `_paymentRequestReject`
     * which will be called during handling of the payment status.
     *
     * @param {string} cid
     * @returns {Promise<boolean>}
     */
    send_payment_request: function (cid) {
        this._super.apply(this, arguments);
        this._reset_state();
        return new Promise((resolve, reject) => {
            this._paymentRequestResolve = (val) => {
                if (!this.hasWaitingPaymentRequest) return;
                this.hasWaitingPaymentRequest = false;
                resolve(val);
            };
            this._paymentRequestReject = (error) => {
                if (!this.hasWaitingPaymentRequest) return;
                this.hasWaitingPaymentRequest = false;
                reject(error)
            };
            this._adyen_pay(cid);
        });
    },
    send_payment_cancel: function (order, cid) {
        this._super.apply(this, arguments);
        return this._adyen_cancel().then((result) => {
            // Unlock the payment method to make new payment requests.
            if (this._paymentRequestReject) {
                this._paymentRequestReject();
            }
            return result;
        });
    },
    close: function () {
        this._super.apply(this, arguments);
    },
    /**
     * This method works together with `send_payment_request`.
     * It handles the reception of payment status.
     *
     * @param {*} paymentStatus
     */
    handleAsyncPaymentStatus: function (paymentStatus, order, payment) {
        try {
            this._paymentRequestResolve(this.validatePaymentStatus(paymentStatus, order, payment));
        } catch (error) {
            Gui.showPopup('ErrorTracebackPopup', { title: error.message, body: error.stack });
        } finally {
            this._reset_state();
        }
    },
    validatePaymentStatus: function (status, order, payment) {
        var self = this;
        var notification = status.latest_response;
        var last_diagnosis_service_id = status.last_received_diagnosis_id;

        if (self.last_diagnosis_service_id != last_diagnosis_service_id) {
            self.last_diagnosis_service_id = last_diagnosis_service_id;
        }

        if (notification && notification.SaleToPOIResponse.MessageHeader.ServiceID == payment.terminalServiceId) {
            var response = notification.SaleToPOIResponse.PaymentResponse.Response;
            var additional_response = new URLSearchParams(response.AdditionalResponse);

            if (response.Result == 'Success') {
                var config = self.pos.config;
                var payment_response = notification.SaleToPOIResponse.PaymentResponse;
                var payment_result = payment_response.PaymentResult;

                var cashier_receipt = payment_response.PaymentReceipt.find(function (receipt) {
                    return receipt.DocumentQualifier == 'CashierReceipt';
                });

                if (cashier_receipt) {
                    payment.set_cashier_receipt(self._convert_receipt_info(cashier_receipt.OutputContent.OutputText));
                }

                var customer_receipt = payment_response.PaymentReceipt.find(function (receipt) {
                    return receipt.DocumentQualifier == 'CustomerReceipt';
                });

                if (customer_receipt) {
                    payment.set_receipt_info(self._convert_receipt_info(customer_receipt.OutputContent.OutputText));
                }

                var tip_amount = payment_result.AmountsResp.TipAmount;
                if (config.adyen_ask_customer_for_tip && tip_amount > 0) {
                    order.set_tip(tip_amount);
                    payment.set_amount(payment_result.AmountsResp.AuthorizedAmount);
                }

                payment.transaction_id = additional_response.get('pspReference');
                payment.card_type = additional_response.get('cardType');
                payment.cardholder_name = additional_response.get('cardHolderName') || '';
                return true;
            } else {
                var message = additional_response.get('message');
                self._show_error(_.str.sprintf(_t('Message from Adyen: %s'), message));
                // No need to discriminate the message since resolving to false will set the payment status to 'retry'.
                return false;
            }
        }
        // /!\ At this point, the received payment status is not handled because the service id is different
        // from the `terminalServiceId`. Should we really ignore this stray payment status?
        // Also, the latest_response is false.
    },
    identifyOrder(status) {
        if (!status.latest_response) return;
        return this.pos.orders.find(
            (order) =>
                order.uid == status.latest_response.SaleToPOIResponse.PaymentResponse.SaleData.SaleTransactionID.TransactionID
        );
    },

    pending_adyen_line() {
      return this.pos.get_order().paymentlines.find(
        paymentLine => paymentLine.payment_method.use_payment_terminal === 'adyen' && (!paymentLine.is_done()));
    },

    // private methods
    _reset_state: function () {
        this.last_diagnosis_service_id = false;
        this.hasWaitingPaymentRequest = false;
    },

    _handle_odoo_connection_failure: function (data) {
        // handle timeout
        var line = this.pending_adyen_line();
        if (line) {
            line.set_payment_status('retry');
        }
        this._show_error(_t('Could not connect to the Odoo server, please check your internet connection and try again.'));

        return Promise.reject(data); // prevent subsequent onFullFilled's from being called
    },

    _call_adyen: function (data, operation) {
        return this.pos.env.services.rpc({
            model: 'pos.payment.method',
            method: 'proxy_adyen_request',
            args: [[this.payment_method.id], data, operation],
        }, {
            // When a payment terminal is disconnected it takes Adyen
            // a while to return an error (~6s). So wait 10 seconds
            // before concluding Odoo is unreachable.
            timeout: 10000,
            shadow: true,
        }).catch(this._handle_odoo_connection_failure.bind(this));
    },

    _adyen_get_sale_id: function () {
        var config = this.pos.config;
        return _.str.sprintf('%s (ID: %s)', config.display_name, config.id);
    },

    _generateServiceId: function() {
        const serviceId = Math.floor(Math.random() * Math.pow(2, 64)).toString(); // random ID to identify request/response pairs
        return serviceId.substring(0, 10); // max length is 10
    },

    _adyen_common_message_header: function (serviceId) {
        return {
            'ProtocolVersion': '3.0',
            'MessageClass': 'Service',
            'MessageType': 'Request',
            'SaleID': this._adyen_get_sale_id(),
            'ServiceID': serviceId,
            'POIID': this.payment_method.adyen_terminal_identifier
        };
    },

    _adyen_pay_data: function () {
        var order = this.pos.get_order();
        var config = this.pos.config;
        var line = order.selected_paymentline;

        const serviceId = this._generateServiceId();
        line.terminalServiceId = serviceId;

        var data = {
            'SaleToPOIRequest': {
                'MessageHeader': _.extend(this._adyen_common_message_header(serviceId), {
                    'MessageCategory': 'Payment',
                }),
                'PaymentRequest': {
                    'SaleData': {
                        'SaleTransactionID': {
                            'TransactionID': order.uid,
                            'TimeStamp': moment().format(), // iso format: '2018-01-10T11:30:15+00:00'
                        }
                    },
                    'PaymentTransaction': {
                        'AmountsReq': {
                            'Currency': this.pos.currency.name,
                            'RequestedAmount': line.amount,
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

    _adyen_pay: function (cid) {
        var self = this;
        var order = this.pos.get_order();

        if (order.selected_paymentline.amount < 0) {
            this._show_error(_t('Cannot process transactions with negative amount.'));
            return this._paymentRequestResolve(false);
        }

        var data = this._adyen_pay_data();
        return this._call_adyen(data).then(function (data) {
            return self._adyen_handle_response(data);
        });
    },

    _adyen_cancel: function (ignore_error) {
        var self = this;
        const order = this.pos.get_order();
        const payment = order.selected_paymentline;

        const serviceId = this._generateServiceId();

        var header = _.extend(this._adyen_common_message_header(serviceId), {
            'MessageCategory': 'Abort',
        });

        var data = {
            'SaleToPOIRequest': {
                'MessageHeader': header,
                'AbortRequest': {
                    'AbortReason': 'MerchantAbort',
                    'MessageReference': {
                        'MessageCategory': 'Payment',
                        'ServiceID': payment.terminalServiceId,
                    }
                },
            }
        };

        return this._call_adyen(data).then(function (data) {

            // Only valid response is a 200 OK HTTP response which is
            // represented by true. So we should check if data == true.
            if (! ignore_error && data !== true) {
                self._show_error(_t('Cancelling the payment failed. Please cancel it manually on the payment terminal.'));
                return false;
            }
            // Cancel is successful.
            return true;
        });
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

    /**
     * /!\ When error, we should not resolve the payment request here because setting of payment status
     * and showing of error is already handled. Resolving the request to false will just set the payment
     * status to retry. Apparently, the business logic here assumes force done if there is error.
     */
    _adyen_handle_response: function (response) {
        var line = this.pending_adyen_line();

        if (response.error && response.error.status_code == 401) {
            this._show_error(_t('Authentication failed. Please check your Adyen credentials.'));
            line.set_payment_status('force_done');
            return this._paymentRequestReject();
        }

        response = response.SaleToPOIRequest;
        if (response && response.EventNotification && response.EventNotification.EventToNotify == 'Reject') {
            console.error('error from Adyen', response);

            var msg = '';
            if (response.EventNotification) {
                var params = new URLSearchParams(response.EventNotification.EventDetails);
                msg = params.get('message');
            }

            this._show_error(_.str.sprintf(_t('An unexpected error occurred. Message from Adyen: %s'), msg));
            if (line) {
                line.set_payment_status('force_done');
            }

            return this._paymentRequestReject();
        } else {
            line.set_payment_status('waitingCard');
            this.hasWaitingPaymentRequest = true;
        }
    },

    _show_error: function (msg, title) {
        if (!title) {
            title =  _t('Adyen Error');
        }
        return Gui.showPopup('ErrorPopup',{
            'title': title,
            'body': msg,
        });
    },
});

return PaymentAdyen;
});
