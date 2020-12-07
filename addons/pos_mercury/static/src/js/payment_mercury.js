odoo.define('pos_mercury.payment', function (require) {
    'use strict';

    const rpc = require('web.rpc');
    const { _t } = require('web.core');
    const { PaymentInterface, registerImplementation } = require('point_of_sale.PaymentInterface');

    // Lookup table to store status and error messages
    const lookUpCodeTransaction = {
        Approved: {
            '000000': _t('Transaction approved'),
        },
        TimeoutError: {
            '001006': 'Global API Not Initialized',
            '001007': 'Timeout on Response',
            '003003': 'Socket Error sending request',
            '003004': 'Socket already open or in use',
            '003005': 'Socket Creation Failed',
            '003006': 'Socket Connection Failed',
            '003007': 'Connection Lost',
            '003008': 'TCP/IP Failed to Initialize',
            '003010': 'Time Out waiting for server response',
            '003011': 'Connect Canceled',
            '003053': 'Initialize Failed',
            '009999': 'Unknown Error',
        },
        FatalError: {
            '-1': 'Timeout error',
            '001001': 'General Failure',
            '001003': 'Invalid Command Format',
            '001004': 'Insufficient Fields',
            '001011': 'Empty Command String',
            '002000': 'Password Verified',
            '002001': 'Queue Full',
            '002002': 'Password Failed – Disconnecting',
            '002003': 'System Going Offline',
            '002004': 'Disconnecting Socket',
            '002006': 'Refused ‘Max Connections’',
            '002008': 'Duplicate Serial Number Detected',
            '002009': 'Password Failed (Client / Server)',
            '002010': 'Password failed (Challenge / Response)',
            '002011': 'Internal Server Error – Call Provider',
            '003002': 'In Process with server',
            '003009': 'Control failed to find branded serial (password lookup failed)',
            '003012': '128 bit CryptoAPI failed',
            '003014': 'Threaded Auth Started Expect Response',
            '003017': 'Failed to start Event Thread.',
            '003050': 'XML Parse Error',
            '003051': 'All Connections Failed',
            '003052': 'Server Login Failed',
            '004001': 'Global Response Length Error (Too Short)',
            '004002': 'Unable to Parse Response from Global (Indistinguishable)',
            '004003': 'Global String Error',
            '004004': 'Weak Encryption Request Not Supported',
            '004005': 'Clear Text Request Not Supported',
            '004010': 'Unrecognized Request Format',
            '004011': 'Error Occurred While Decrypting Request',
            '004017': 'Invalid Check Digit',
            '004018': 'Merchant ID Missing',
            '004019': 'TStream Type Missing',
            '004020': 'Could Not Encrypt Response- Call Provider',
            100201: 'Invalid Transaction Type',
            100202: 'Invalid Operator ID',
            100203: 'Invalid Memo',
            100204: 'Invalid Account Number',
            100205: 'Invalid Expiration Date',
            100206: 'Invalid Authorization Code',
            100207: 'Invalid Authorization Code',
            100208: 'Invalid Authorization Amount',
            100209: 'Invalid Cash Back Amount',
            100210: 'Invalid Gratuity Amount',
            100211: 'Invalid Purchase Amount',
            100212: 'Invalid Magnetic Stripe Data',
            100213: 'Invalid PIN Block Data',
            100214: 'Invalid Derived Key Data',
            100215: 'Invalid State Code',
            100216: 'Invalid Date of Birth',
            100217: 'Invalid Check Type',
            100218: 'Invalid Routing Number',
            100219: 'Invalid TranCode',
            100220: 'Invalid Merchant ID',
            100221: 'Invalid TStream Type',
            100222: 'Invalid Batch Number',
            100223: 'Invalid Batch Item Count',
            100224: 'Invalid MICR Input Type',
            100225: 'Invalid Driver’s License',
            100226: 'Invalid Sequence Number',
            100227: 'Invalid Pass Data',
            100228: 'Invalid Card Type',
        },
    };

    const PaymentMercury = PaymentInterface.extend({
        init() {
            this._super(...arguments);
            // How long we wait for the odoo server to deliver the response of
            // a Vantiv transaction
            this.server_timeout_in_ms = 95000;
            // How many Vantiv transactions we send without receiving a
            // response
            this.server_retries = 3;
            this.enable_reversals();
        },
        send_payment_request: function (paymentId, parsed_result) {
            this._super.apply(this, arguments);
            const payment = this.model.getRecord('pos.payment', paymentId);
            return this.credit_code_transaction(payment, parsed_result);
        },
        send_payment_reversal: function (paymentId) {
            this._super.apply(this, arguments);
            const payment = this.model.getRecord('pos.payment', paymentId);
            return this.do_reversal(payment);
        },

        //#region PRIVATE METHODS

        async credit_code_transaction(payment, parsed_result, deferred, retry_nr) {
            const order = this.model.getRecord('pos.order', payment.pos_order_id);

            if (this.model.floatCompare(payment.amount, 0) < 0) {
                this.model.ui.askUser('ErrorPopup', {
                    title: _t('Refunds not supported'),
                    body: _t(
                        "Credit card refunds are not supported. Instead select your credit card payment method, click 'Validate' and refund the original charge manually through the Vantiv backend."
                    ),
                });
                return false;
            }

            const decodedMagtek = this.model.decodeMagtek(parsed_result.code);

            if (!decodedMagtek) {
                this.model.ui.askUser('ErrorPopup', {
                    title: _t('Could not read card'),
                    body: _t(
                        'This can be caused by a badly executed swipe or by not having your keyboard layout set to US QWERTY (not US International).'
                    ),
                });
                return false;
            }

            const transaction = {
                encrypted_key: decodedMagtek['encrypted_key'],
                encrypted_block: decodedMagtek['encrypted_block'],
                transaction_type: 'Credit',
                transaction_code: 'Sale',
                invoice_no: order.id.replace(/-/g, ''),
                purchase: payment.amount,
                payment_method_id: payment.payment_method_id,
            };

            if (!deferred) {
                deferred = new $.Deferred();
                this.model.ui.askUser('PaymentTransactionPopup', {
                    transaction: deferred,
                });
                deferred.notify({
                    message: _t('Handling transaction...'),
                });
            }

            retry_nr = retry_nr || 0;

            try {
                const paymentResult = await rpc.query(
                    {
                        model: 'pos_mercury.mercury_transaction',
                        method: 'do_payment',
                        args: [transaction],
                    },
                    {
                        timeout: this.server_timeout_in_ms,
                    }
                );
                if (paymentResult === 'timeout') {
                    if (data === 'timeout') {
                        await this.retry_mercury_transaction(
                            deferred,
                            null,
                            retry_nr,
                            true,
                            this.credit_code_transaction,
                            [payment, parsed_result, deferred, retry_nr + 1]
                        );
                    }
                } else if (paymentResult === 'not setup') {
                    deferred.resolve({
                        message: _t('Please setup your Vantiv merchant account.'),
                    });
                    return false;
                } else if (paymentResult === 'internal error') {
                    deferred.resolve({
                        message: _t('Odoo error while processing transaction.'),
                    });
                    return false;
                } else {
                    const response = this.model.decodeMercuryResponse(paymentResult);
                    response.payment_method_id = payment.payment_method_id;

                    if (response.status === 'Approved') {
                        // AP* indicates a duplicate request, so don't add anything for those
                        if (
                            response.message === 'AP*' &&
                            this._does_credit_payment_line_exist(
                                response.authorize,
                                decodedMagtek['number'],
                                response.card_type,
                                decodedMagtek['name']
                            )
                        ) {
                            deferred.resolve({
                                message: lookUpCodeTransaction['Approved'][response.error],
                                auto_close: true,
                            });
                            return false;
                        } else {
                            const vals = {
                                amount: response.authorize,
                                mercury_card_number: decodedMagtek['number'],
                                mercury_card_brand: response.card_type,
                                mercury_card_owner_name: decodedMagtek['name'],
                                mercury_ref_no: response.ref_no,
                                mercury_record_no: response.record_no,
                                mercury_invoice_no: response.invoice_no,
                                name: this.model.getMercuryPaymentName(payment),
                            };
                            const extras = {
                                mercury_amount: response.authorize,
                                mercury_auth_code: response.auth_code,
                                mercury_data: response,
                            };

                            await this.model.noMutexActionHandler({
                                name: 'actionUpdatePayment',
                                args: [payment, vals, extras],
                            });

                            if (response.message === 'PARTIAL AP') {
                                deferred.resolve({
                                    message: _t('Partially approved'),
                                    auto_close: false,
                                });
                                return true;
                            } else {
                                deferred.resolve({
                                    message: lookUpCodeTransaction['Approved'][response.error],
                                    auto_close: true,
                                });
                                return true;
                            }
                        }
                    } else {
                        // if an error related to timeout or connectivity issues arised, then retry the same transaction
                        if (lookUpCodeTransaction['TimeoutError'][response.error]) {
                            // recoverable error
                            return await this.retry_mercury_transaction(
                                deferred,
                                response,
                                retry_nr,
                                true,
                                this.credit_code_transaction,
                                [payment, parsed_result, deferred, retry_nr + 1]
                            );
                        } else {
                            // not recoverable
                            deferred.resolve({
                                message: 'Error ' + response.error + ':<br/>' + response.message,
                                auto_close: false,
                            });
                            return false;
                        }
                    }
                }
            } catch (error) {
                return await this.retry_mercury_transaction(
                    deferred,
                    null,
                    retry_nr,
                    false,
                    this.credit_code_transaction.bind(this),
                    [payment, parsed_result, deferred, retry_nr + 1]
                );
            }
        },
        async do_reversal(payment, is_voidsale, deferred, retry_nr) {
            retry_nr = retry_nr || 0;

            const request_data = _.extend(
                {
                    transaction_type: 'Credit',
                    transaction_code: 'VoidSaleByRecordNo',
                },
                payment._extras.mercury_data
            );

            let message = '';
            let rpc_method = '';

            if (is_voidsale) {
                message = _t('Reversal failed, sending VoidSale...');
                rpc_method = 'do_voidsale';
            } else {
                message = _t('Sending reversal...');
                rpc_method = 'do_reversal';
            }

            if (!deferred) {
                deferred = new $.Deferred();
                // show the transaction popup.
                // the transaction deferred is used to update transaction status
                this.model.ui.askUser('PaymentTransactionPopup', {
                    transaction: deferred,
                });
            }
            deferred.notify({
                message: message,
            });
            try {
                const result = await rpc.query(
                    {
                        model: 'pos_mercury.mercury_transaction',
                        method: rpc_method,
                        args: [request_data],
                    },
                    {
                        timeout: this.server_timeout_in_ms,
                    }
                );
                if (result === 'timeout') {
                    return await this.retry_mercury_transaction(
                        deferred,
                        null,
                        retry_nr,
                        true,
                        this.do_reversal.bind(this),
                        [payment, is_voidsale, deferred, retry_nr + 1]
                    );
                }

                if (result === 'internal error') {
                    deferred.resolve({
                        message: _t('Odoo error while processing transaction.'),
                    });
                    return false;
                }

                const response = this.model.decodeMercuryResponse(result);

                if (!is_voidsale) {
                    if (response.status != 'Approved' || response.message != 'REVERSED') {
                        // reversal was not successful, send voidsale
                        return await this.do_reversal(payment, true, deferred, retry_nr);
                    } else {
                        // reversal was successful
                        deferred.resolve({
                            message: _t('Reversal succeeded'),
                        });
                        return true;
                    }
                } else {
                    // voidsale ended, nothing more we can do
                    if (response.status === 'Approved') {
                        deferred.resolve({
                            message: _t('VoidSale succeeded'),
                        });
                        return true;
                    } else {
                        deferred.resolve({
                            message: 'Error ' + response.error + ':<br/>' + response.message,
                        });
                        return false;
                    }
                }
            } catch (error) {
                return await this.retry_mercury_transaction(
                    deferred,
                    null,
                    retry_nr,
                    false,
                    this.do_reversal.bind(this),
                    [payment, is_voidsale, deferred, retry_nr + 1]
                );
            }
        },
        async retry_mercury_transaction(def, response, retry_nr, can_connect_to_server, callback, args) {
            var message = '';

            if (retry_nr < this.server_retries) {
                if (response) {
                    message = 'Retry #' + (retry_nr + 1) + '...<br/><br/>' + response.message;
                } else {
                    message = 'Retry #' + (retry_nr + 1) + '...';
                }
                def.notify({
                    message: message,
                });
                return await new Promise((resolve) => {
                    // Wait for 1 sec to retry the request.
                    setTimeout(async () => {
                        resolve(await callback.apply(this, args));
                    }, 1000);
                });
            } else {
                if (response) {
                    message =
                        'Error ' +
                        response.error +
                        ': ' +
                        lookUpCodeTransaction['TimeoutError'][response.error] +
                        '<br/>' +
                        response.message;
                } else {
                    if (can_connect_to_server) {
                        message = _t('No response from Vantiv (Vantiv down?)');
                    } else {
                        message = _t('No response from server (connected to network?)');
                    }
                }
                def.resolve({
                    message: message,
                    auto_close: false,
                });
                return false;
            }
        },
        _does_credit_payment_line_exist(amount, card_number, card_brand, card_owner_name) {
            for (const payment of this.model.getPayments(props.activeOrder)) {
                if (
                    payment._extras.mercury_amount === amount &&
                    payment.mercury_card_number === card_number &&
                    payment.mercury_card_brand === card_brand &&
                    payment.mercury_card_owner_name === card_owner_name
                ) {
                    return true;
                }
            }
            return false;
        },

        //#endregion PRIVATE METHODS
    });

    registerImplementation('mercury', PaymentMercury);

    return PaymentMercury;
});
