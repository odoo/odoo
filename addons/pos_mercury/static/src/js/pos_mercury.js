odoo.define('pos_mercury.pos_mercury', function (require) {
"use strict";

var pos_model = require('point_of_sale.models');

pos_model.load_fields('pos.payment.method', 'pos_mercury_config_id');

pos_model.PosModel = pos_model.PosModel.extend({
    getOnlinePaymentMethods: function () {
        var online_payment_methods = [];

        $.each(this.payment_methods, function (i, payment_method) {
            if (payment_method.pos_mercury_config_id) {
                online_payment_methods.push({label: payment_method.name, item: payment_method.id});
            }
        });

        return online_payment_methods;
    },
    decodeMagtek: function (magtekInput) {
        // Regular expression to identify and extract data from the track 1 & 2 of the magnetic code
        var _track1_regex = /%B?([0-9]*)\^([A-Z\/ -_]*)\^([0-9]{4})(.{3})([^?]+)\?/;

        var track1 = magtekInput.match(_track1_regex);
        var magtek_generated = magtekInput.split('|');

        var to_return = {};
        try {
            track1.shift(); // get rid of complete match
            to_return['number'] = track1.shift().substr(-4);
            to_return['name'] = track1.shift();
            track1.shift(); // expiration date
            track1.shift(); // service code
            track1.shift(); // discretionary data
            track1.shift(); // zero pad

            magtek_generated.shift(); // track1 and track2
            magtek_generated.shift(); // clear text crc
            magtek_generated.shift(); // encryption counter
            to_return['encrypted_block'] = magtek_generated.shift();
            magtek_generated.shift(); // enc session id
            magtek_generated.shift(); // device serial
            magtek_generated.shift(); // magneprint data
            magtek_generated.shift(); // magneprint status
            magtek_generated.shift(); // enc track3
            to_return['encrypted_key'] = magtek_generated.shift();
            magtek_generated.shift(); // enc track1
            magtek_generated.shift(); // reader enc status

            return to_return;
        } catch (e) {
            return 0;
        }
    },
    decodeMercuryResponse: function (data) {
        // get rid of xml version declaration and just keep the RStream
        // from the response because the xml contains two version
        // declarations. One for the SOAP, and one for the content. Maybe
        // we should unpack the SOAP layer in python?
        data = data.replace(/.*<\?xml version="1.0"\?>/, "");
        data = data.replace(/<\/CreditTransactionResult>.*/, "");

        var xml = $($.parseXML(data));
        var cmd_response = xml.find("CmdResponse");
        var tran_response = xml.find("TranResponse");

        return {
            status: cmd_response.find("CmdStatus").text(),
            message: cmd_response.find("TextResponse").text(),
            error: cmd_response.find("DSIXReturnCode").text(),
            card_type: tran_response.find("CardType").text(),
            auth_code: tran_response.find("AuthCode").text(),
            acq_ref_data: tran_response.find("AcqRefData").text(),
            process_data: tran_response.find("ProcessData").text(),
            invoice_no: tran_response.find("InvoiceNo").text(),
            ref_no: tran_response.find("RefNo").text(),
            record_no: tran_response.find("RecordNo").text(),
            purchase: parseFloat(tran_response.find("Purchase").text()),
            authorize: parseFloat(tran_response.find("Authorize").text()),
        };
    }
});

var _paylineproto = pos_model.Paymentline.prototype;
pos_model.Paymentline = pos_model.Paymentline.extend({
    init_from_JSON: function (json) {
        _paylineproto.init_from_JSON.apply(this, arguments);

        this.paid = json.paid;
        this.mercury_card_number = json.mercury_card_number;
        this.mercury_card_brand = json.mercury_card_brand;
        this.mercury_card_owner_name = json.mercury_card_owner_name;
        this.mercury_ref_no = json.mercury_ref_no;
        this.mercury_record_no = json.mercury_record_no;
        this.mercury_invoice_no = json.mercury_invoice_no;
        this.mercury_auth_code = json.mercury_auth_code;
        this.mercury_data = json.mercury_data;
        this.mercury_swipe_pending = json.mercury_swipe_pending;

        this.set_credit_card_name();
    },
    export_as_JSON: function () {
        return _.extend(_paylineproto.export_as_JSON.apply(this, arguments), {paid: this.paid,
                                                                              mercury_card_number: this.mercury_card_number,
                                                                              mercury_card_brand: this.mercury_card_brand,
                                                                              mercury_card_owner_name: this.mercury_card_owner_name,
                                                                              mercury_ref_no: this.mercury_ref_no,
                                                                              mercury_record_no: this.mercury_record_no,
                                                                              mercury_invoice_no: this.mercury_invoice_no,
                                                                              mercury_auth_code: this.mercury_auth_code,
                                                                              mercury_data: this.mercury_data,
                                                                              mercury_swipe_pending: this.mercury_swipe_pending});
    },
    set_credit_card_name: function () {
        if (this.mercury_card_number) {
            this.name = this.mercury_card_brand + " (****" + this.mercury_card_number + ")";
        }
    },
    is_done: function () {
        var res = _paylineproto.is_done.apply(this);
        return res && !this.mercury_swipe_pending;
    },
    export_for_printing: function () {
        const result = _paylineproto.export_for_printing.apply(this, arguments);
        result.mercury_data = this.mercury_data;
        result.mercury_auth_code = this.mercury_auth_code;
        return result;
    }
});

<<<<<<< HEAD
var _order_super = pos_model.Order.prototype;
pos_model.Order = pos_model.Order.extend({
    electronic_payment_in_progress: function() {
        var res = _order_super.electronic_payment_in_progress.apply(this, arguments);
        return res || this.get_paymentlines().some(line => line.mercury_swipe_pending);
=======
// On Payment screen, allow online payments
PaymentScreenWidget.include({
    // How long we wait for the odoo server to deliver the response of
    // a Vantiv transaction
    server_timeout_in_ms: 95000,

    // How many Vantiv transactions we send without receiving a
    // response
    server_retries: 3,

    _get_swipe_pending_line: function () {
        var i = 0;
        var lines = this.pos.get_order().get_paymentlines();

        for (i = 0; i < lines.length; i++) {
            if (lines[i].mercury_swipe_pending) {
                return lines[i];
            }
        }

        return 0;
    },

    _does_credit_payment_line_exist: function (amount, card_number, card_brand, card_owner_name) {
        var i = 0;
        var lines = this.pos.get_order().get_paymentlines();

        for (i = 0; i < lines.length; i++) {
            if (lines[i].mercury_amount === amount &&
                lines[i].mercury_card_number === card_number &&
                lines[i].mercury_card_brand === card_brand &&
                lines[i].mercury_card_owner_name === card_owner_name) {
                return true;
            }
        }

        return false;
    },

    retry_mercury_transaction: function (def, response, retry_nr, can_connect_to_server, callback, args) {
        var self = this;
        var message = "";

        if (retry_nr < self.server_retries) {
            if (response) {
                message = "Retry #" + (retry_nr + 1) + "...<br/><br/>" + response.message;
            } else {
                message = "Retry #" + (retry_nr + 1) + "...";
            }
            def.notify({
                message: message
            });

            setTimeout(function () {
                callback.apply(self, args);
            }, 1000);
        } else {
            if (response) {
                message = "Error " + response.error + ": " + lookUpCodeTransaction["TimeoutError"][response.error] + "<br/>" + response.message;
            } else {
                if (can_connect_to_server) {
                    message = _t("No response from Vantiv (Vantiv down?)");
                } else {
                    message = _t("No response from server (connected to network?)");
                }
            }
            def.resolve({
                message: message,
                auto_close: false
            });
        }
    },

    // Handler to manage the card reader string
    credit_code_transaction: function (parsed_result, old_deferred, retry_nr) {
        var order = this.pos.get_order();
        if (order.get_due(order.selected_paymentline) < 0) {
            this.gui.show_popup('error',{
                'title': _t('Refunds not supported'),
                'body':  _t('Credit card refunds are not supported. Instead select your credit card payment method, click \'Validate\' and refund the original charge manually through the Vantiv backend.'),
            });
            return;
        }

        if(this.pos.getOnlinePaymentMethods().length === 0) {
            return;
        }

        var self = this;
        var decodedMagtek = self.pos.decodeMagtek(parsed_result.code);

        if (! decodedMagtek) {
            this.gui.show_popup('error',{
                'title': _t('Could not read card'),
                'body':  _t('This can be caused by a badly executed swipe or by not having your keyboard layout set to US QWERTY (not US International).'),
            });
            return;
        }

        var swipe_pending_line = self._get_swipe_pending_line();
        var purchase_amount = 0;

        if (swipe_pending_line) {
            purchase_amount = swipe_pending_line.get_amount();
        } else {
            purchase_amount = self.pos.get_order().get_due();
        }

        var transaction = {
            'encrypted_key'     : decodedMagtek['encrypted_key'],
            'encrypted_block'   : decodedMagtek['encrypted_block'],
            'transaction_type'  : 'Credit',
            'transaction_code'  : 'Sale',
            'invoice_no'        : self.pos.get_order().uid.replace(/-/g,''),
            'purchase'          : purchase_amount,
            'payment_method_id' : parsed_result.payment_method_id,
        };

        var def = old_deferred || new $.Deferred();
        retry_nr = retry_nr || 0;

        // show the transaction popup.
        // the transaction deferred is used to update transaction status
        // if we have a previous deferred it indicates that this is a retry
        if (! old_deferred) {
            self.gui.show_popup('payment-transaction', {
                transaction: def
            });
            def.notify({
                message: _t('Handling transaction...'),
            });
        }

        rpc.query({
                model: 'pos_mercury.mercury_transaction',
                method: 'do_payment',
                args: [transaction],
            }, {
                timeout: self.server_timeout_in_ms,
            })
            .then(function (data) {
                // if not receiving a response from Vantiv, we should retry
                if (data === "timeout") {
                    self.retry_mercury_transaction(def, null, retry_nr, true, self.credit_code_transaction, [parsed_result, def, retry_nr + 1]);
                    return;
                }

                if (data === "not setup") {
                    def.resolve({
                        message: _t("Please setup your Vantiv merchant account.")
                    });
                    return;
                }

                if (data === "internal error") {
                    def.resolve({
                        message: _t("Odoo error while processing transaction.")
                    });
                    return;
                }

                var response = self.pos.decodeMercuryResponse(data);
                response.payment_method_id = parsed_result.payment_method_id;

                if (response.status === 'Approved') {
                    // AP* indicates a duplicate request, so don't add anything for those
                    if (response.message === "AP*" && self._does_credit_payment_line_exist(response.authorize, decodedMagtek['number'],
                                                                                        response.card_type, decodedMagtek['name'])) {
                        def.resolve({
                            message: lookUpCodeTransaction["Approved"][response.error],
                            auto_close: true,
                        });
                    } else {
                        // If the payment is approved, add a payment line
                        var order = self.pos.get_order();

                        if (swipe_pending_line) {
                            order.select_paymentline(swipe_pending_line);
                        } else {
                            order.add_paymentline(self.pos.payment_methods_by_id[parsed_result.payment_method_id]);
                        }

                        order.selected_paymentline.paid = true;
                        order.selected_paymentline.mercury_swipe_pending = false;
                        order.selected_paymentline.mercury_amount = response.authorize;
                        order.selected_paymentline.set_amount(response.authorize);
                        order.selected_paymentline.mercury_card_number = decodedMagtek['number'];
                        order.selected_paymentline.mercury_card_brand = response.card_type;
                        order.selected_paymentline.mercury_card_owner_name = decodedMagtek['name'];
                        order.selected_paymentline.mercury_ref_no = response.ref_no;
                        order.selected_paymentline.mercury_record_no = response.record_no;
                        order.selected_paymentline.mercury_invoice_no = response.invoice_no;
                        order.selected_paymentline.mercury_auth_code = response.auth_code;
                        order.selected_paymentline.mercury_data = response; // used to reverse transactions
                        order.selected_paymentline.set_credit_card_name();

                        self.order_changes();
                        self.reset_input();
                        self.render_paymentlines();
                        order.trigger('change', order); // needed so that export_to_JSON gets triggered

                        if (response.message === "PARTIAL AP") {
                            def.resolve({
                                message: _t("Partially approved"),
                                auto_close: false,
                            });
                        } else {
                            def.resolve({
                                message: lookUpCodeTransaction["Approved"][response.error],
                                auto_close: true,
                            });
                        }
                    }
                }

                // if an error related to timeout or connectivity issues arised, then retry the same transaction
                else {
                    if (lookUpCodeTransaction["TimeoutError"][response.error]) { // recoverable error
                        self.retry_mercury_transaction(def, response, retry_nr, true, self.credit_code_transaction, [parsed_result, def, retry_nr + 1]);
                    } else { // not recoverable
                        def.resolve({
                            message: "Error " + response.error + ":<br/>" + response.message,
                            auto_close: false
                        });
                    }
                }

            }).catch(function () {
                self.retry_mercury_transaction(def, null, retry_nr, false, self.credit_code_transaction, [parsed_result, def, retry_nr + 1]);
            });
    },

    credit_code_cancel: function () {
        return;
    },

    credit_code_action: function (parsed_result) {
        var self = this;
        var online_payment_methods = this.pos.getOnlinePaymentMethods();

        if (online_payment_methods.length === 1) {
            parsed_result.payment_method_id = online_payment_methods[0].item;
            self.credit_code_transaction(parsed_result);
        } else { // this is for supporting another payment system like mercury
            this.gui.show_popup('selection',{
                title:   _t('Pay with: '),
                list:    online_payment_methods,
                confirm: function (item) {
                    parsed_result.payment_method_id = item;
                    self.credit_code_transaction(parsed_result);
                },
                cancel:  self.credit_code_cancel,
            });
        }
>>>>>>> f7f0c23623b... temp
    },
});

});
