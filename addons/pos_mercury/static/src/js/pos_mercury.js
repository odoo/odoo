odoo.define('pos_mercury.pos_mercury', function (require) {
"use strict";

var core    = require('web.core');
var rpc    = require('web.rpc');
var screens = require('point_of_sale.screens');
var gui     = require('point_of_sale.gui');
var pos_model = require('point_of_sale.models');

var _t      = core._t;

var PopupWidget = require('point_of_sale.popups');
var ScreenWidget = screens.ScreenWidget;
var PaymentScreenWidget = screens.PaymentScreenWidget;

pos_model.load_fields("account.journal", "pos_mercury_config_id");

pos_model.PosModel = pos_model.PosModel.extend({
    getOnlinePaymentJournals: function () {
        var self = this;
        var online_payment_journals = [];

        $.each(this.journals, function (i, val) {
            if (val.pos_mercury_config_id) {
                online_payment_journals.push({label:self.getCashRegisterByJournalID(val.id).journal_id[1], item:val.id});
            }
        });

        return online_payment_journals;
    },
    getCashRegisterByJournalID: function (journal_id) {
        var cashregister_return;

        $.each(this.cashregisters, function (index, cashregister) {
            if (cashregister.journal_id[0] === journal_id) {
                cashregister_return = cashregister;
            }
        });

        return cashregister_return;
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
    }
});

// Lookup table to store status and error messages
var lookUpCodeTransaction = {
    'Approved': {
        '000000': _t('Transaction approved'),
    },
    'TimeoutError': {
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
    'FatalError': {
        '-1':     'Timeout error',
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
        '100201': 'Invalid Transaction Type',
        '100202': 'Invalid Operator ID',
        '100203': 'Invalid Memo',
        '100204': 'Invalid Account Number',
        '100205': 'Invalid Expiration Date',
        '100206': 'Invalid Authorization Code',
        '100207': 'Invalid Authorization Code',
        '100208': 'Invalid Authorization Amount',
        '100209': 'Invalid Cash Back Amount',
        '100210': 'Invalid Gratuity Amount',
        '100211': 'Invalid Purchase Amount',
        '100212': 'Invalid Magnetic Stripe Data',
        '100213': 'Invalid PIN Block Data',
        '100214': 'Invalid Derived Key Data',
        '100215': 'Invalid State Code',
        '100216': 'Invalid Date of Birth',
        '100217': 'Invalid Check Type',
        '100218': 'Invalid Routing Number',
        '100219': 'Invalid TranCode',
        '100220': 'Invalid Merchant ID',
        '100221': 'Invalid TStream Type',
        '100222': 'Invalid Batch Number',
        '100223': 'Invalid Batch Item Count',
        '100224': 'Invalid MICR Input Type',
        '100225': 'Invalid Driver’s License',
        '100226': 'Invalid Sequence Number',
        '100227': 'Invalid Pass Data',
        '100228': 'Invalid Card Type',
    },
};
// Popup to show all transaction state for the payment.

var PaymentTransactionPopupWidget = PopupWidget.extend({
    template: 'PaymentTransactionPopupWidget',
    show: function (options) {
        var self = this;
        this._super(options);
        options.transaction.then(function (data) {
            if (data.auto_close) {
                setTimeout(function () {
                    self.gui.close_popup();
                }, 2000);
            } else {
                self.close();
                self.$el.find('.popup').append('<div class="footer"><div class="button cancel">Ok</div></div>');
            }

            self.$el.find('p.body').html(data.message);
        }).progress(function (data) {
            self.$el.find('p.body').html(data.message);
        });
    }
});

gui.define_popup({name:'payment-transaction', widget: PaymentTransactionPopupWidget});

// On all screens, if a card is swipped, return a popup error.
ScreenWidget.include({
    credit_error_action: function () {
        this.gui.show_popup('error-barcode',_t('Go to payment screen to use cards'));
    },

    show: function () {
        this._super();
        if(this.pos.getOnlinePaymentJournals().length !== 0) {
            this.pos.barcode_reader.set_action_callback('credit', _.bind(this.credit_error_action, this));
        }
    }
});

// On Payment screen, allow online payments
PaymentScreenWidget.include({
    // How long we wait for the odoo server to deliver the response of
    // a Mercury transaction
    server_timeout_in_ms: 95000,

    // How many Mercury transactions we send without receiving a
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
                    message = _t("No response from Mercury (Mercury down?)");
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

        if(this.pos.getOnlinePaymentJournals().length === 0) {
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
            'journal_id'        : parsed_result.journal_id,
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
                // if not receiving a response from Mercury, we should retry
                if (data === "timeout") {
                    self.retry_mercury_transaction(def, null, retry_nr, true, self.credit_code_transaction, [parsed_result, def, retry_nr + 1]);
                    return;
                }

                if (data === "not setup") {
                    def.resolve({
                        message: _t("Please setup your Mercury merchant account.")
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
                response.journal_id = parsed_result.journal_id;

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
                            order.add_paymentline(self.pos.getCashRegisterByJournalID(parsed_result.journal_id));
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

            }).fail(function (type, error) {
                self.retry_mercury_transaction(def, null, retry_nr, false, self.credit_code_transaction, [parsed_result, def, retry_nr + 1]);
            });
    },

    credit_code_cancel: function () {
        return;
    },

    credit_code_action: function (parsed_result) {
        var self = this;
        var online_payment_journals = this.pos.getOnlinePaymentJournals();

        if (online_payment_journals.length === 1) {
            parsed_result.journal_id = online_payment_journals[0].item;
            self.credit_code_transaction(parsed_result);
        } else { // this is for supporting another payment system like mercury
            this.gui.show_popup('selection',{
                title:   _t('Pay with: '),
                list:    online_payment_journals,
                confirm: function (item) {
                    parsed_result.journal_id = item;
                    self.credit_code_transaction(parsed_result);
                },
                cancel:  self.credit_code_cancel,
            });
        }
    },

    remove_paymentline_by_ref: function (line) {
        this.pos.get_order().remove_paymentline(line);
        this.reset_input();
        this.render_paymentlines();
    },

    do_reversal: function (line, is_voidsale, old_deferred, retry_nr) {
        var def = old_deferred || new $.Deferred();
        var self = this;
        retry_nr = retry_nr || 0;

        // show the transaction popup.
        // the transaction deferred is used to update transaction status
        this.gui.show_popup('payment-transaction', {
            transaction: def
        });

        var request_data = _.extend({
            'transaction_type': 'Credit',
            'transaction_code': 'VoidSaleByRecordNo',
        }, line.mercury_data);

        var message = "";
        var rpc_method = "";

        if (is_voidsale) {
            message = _t("Reversal failed, sending VoidSale...");
            rpc_method = "do_voidsale";
        } else {
            message = _t("Sending reversal...");
            rpc_method = "do_reversal";
        }

        if (! old_deferred) {
            def.notify({
                message: message,
            });
        }

        rpc.query({
                model: 'pos_mercury.mercury_transaction',
                method: rpc_method,
                args: [request_data],
            }, {
                timeout: self.server_timeout_in_ms
            })
            .then(function (data) {
                if (data === "timeout") {
                    self.retry_mercury_transaction(def, null, retry_nr, true, self.do_reversal, [line, is_voidsale, def, retry_nr + 1]);
                    return;
                }

                if (data === "internal error") {
                    def.resolve({
                        message: _t("Odoo error while processing transaction.")
                    });
                    return;
                }

                var response = self.pos.decodeMercuryResponse(data);

                if (! is_voidsale) {
                    if (response.status != 'Approved' || response.message != 'REVERSED') {
                        // reversal was not successful, send voidsale
                        self.do_reversal(line, true);
                    } else {
                        // reversal was successful
                        def.resolve({
                            message: _t("Reversal succeeded"),
                        });

                        self.remove_paymentline_by_ref(line);
                    }
                } else { // voidsale ended, nothing more we can do
                    if (response.status === 'Approved') {
                        def.resolve({
                            message: _t("VoidSale succeeded"),
                        });

                        self.remove_paymentline_by_ref(line);
                    } else {
                        def.resolve({
                            message: "Error " + response.error + ":<br/>" + response.message,
                        });
                    }
                }
            }).fail(function (type, error) {
                self.retry_mercury_transaction(def, null, retry_nr, false, self.do_reversal, [line, is_voidsale, def, retry_nr + 1]);
            });
    },

    click_delete_paymentline: function (cid) {
        var lines = this.pos.get_order().get_paymentlines();

        for (var i = 0; i < lines.length; i++) {
            if (lines[i].cid === cid && lines[i].mercury_data) {
                this.do_reversal(lines[i], false);
                return;
            }
        }

        this._super(cid);
    },

    // make sure there is only one paymentline waiting for a swipe
    click_paymentmethods: function (id) {
        var i;
        var order = this.pos.get_order();
        var cashregister = null;
        for (i = 0; i < this.pos.cashregisters.length; i++) {
            if (this.pos.cashregisters[i].journal_id[0] === id){
                cashregister = this.pos.cashregisters[i];
                break;
            }
        }

        if (cashregister.journal.pos_mercury_config_id) {
            var already_swipe_pending = false;
            var lines = order.get_paymentlines();

            for (i = 0; i < lines.length; i++) {
                if (lines[i].cashregister.journal.pos_mercury_config_id && lines[i].mercury_swipe_pending) {
                    already_swipe_pending = true;
                }
            }

            if (already_swipe_pending) {
                this.gui.show_popup('error',{
                    'title': _t('Error'),
                    'body':  _t('One credit card swipe already pending.'),
                });
            } else {
                this._super(id);
                if (order.get_due(order.selected_paymentline) > 0) {
                    order.selected_paymentline.mercury_swipe_pending = true;
                    this.render_paymentlines();
                    order.trigger('change', order); // needed so that export_to_JSON gets triggered
                }
            }
        } else {
            this._super(id);
        }
    },

    show: function () {
        this._super();
        if (this.pos.getOnlinePaymentJournals().length !== 0) {
            this.pos.barcode_reader.set_action_callback('credit', _.bind(this.credit_code_action, this));
        }
    },

    // before validating, get rid of any paymentlines that are waiting
    // on a swipe.
    validate_order: function(force_validation) {
        if (this.pos.get_order().is_paid() && ! this.invoicing) {
            var lines = this.pos.get_order().get_paymentlines();

            for (var i = 0; i < lines.length; i++) {
                if (lines[i].mercury_swipe_pending) {
                    this.pos.get_order().remove_paymentline(lines[i]);
                    this.render_paymentlines();
                }
            }
        }

        this._super(force_validation);
    }
});

});
