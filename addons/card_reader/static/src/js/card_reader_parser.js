odoo.define('card_reader.MagneticParser', function (require) {
"use strict";

var Class   = require('web.Class');
var Model   = require('web.Model');
var session = require('web.session');
var core    = require('web.core');
var screens = require('point_of_sale.screens');
var gui     = require('point_of_sale.gui');
var pos_model = require('point_of_sale.models');
var utils = require('web.utils');

var Qweb    = core.qweb;
var _t      = core._t;

Qweb.add_template('/card_reader/static/src/xml/templates.xml');

var BarcodeParser = require('barcodes.BarcodeParser');
var PopupWidget = require('point_of_sale.popups');
var ScreenWidget = screens.ScreenWidget;
var PaymentScreenWidget = screens.PaymentScreenWidget;
var round_pr = utils.round_precision;

var onlinePaymentJournal = [];

var allowOnlinePayment = function (pos) {
    if (onlinePaymentJournal.length) {
        return true;
    }
    $.each(pos.journals, function (i, val) {
        if (val.card_reader_config_id) {
            onlinePaymentJournal.push({label:val.display_name, item:val.id});
        }
    });
    return onlinePaymentJournal.length;
};

// Popup declaration to ask for confirmation before an electronic payment
var PaymentConfirmPopupWidget = PopupWidget.extend({
    template: 'PaymentConfirmPopupWidget',
    show: function (options) {
        this._super(options);
    }
});

function getCashRegisterByJournalID (cashRegisters, journal_id) {
    var cashRegisterReturn;

    $.each(cashRegisters, function (index, cashRegister) {
        if (cashRegister.journal_id[0] == journal_id) {
            cashRegisterReturn = cashRegister;
        }
    });

    return cashRegisterReturn;
}

function decodeMercuryResponse (data) {
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

function decodeMagtek (magtekInput) {
    // Regular expression to identify and extract data from the track 1 & 2 of the magnetic code
    var _track1_regex = /%B?([0-9]*)\^([A-Z\/ -_]*)\^([0-9]{4})(.{3})([^?]+)\?/;

    var track1 = magtekInput.match(_track1_regex);
    var magtek_generated = magtekInput.split('|');

    var to_return = {};
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
}

var _paylineproto = pos_model.Paymentline.prototype;
pos_model.Paymentline = pos_model.Paymentline.extend({
    init_from_JSON: function (json) {
        _paylineproto.init_from_JSON.apply(this, arguments);
        this.paid = json.paid;
        this.mercury_data = json.mercury_data;
        this.swipe_pending = json.swipe_pending;
    },
    export_as_JSON: function () {
        return _.extend(_paylineproto.export_as_JSON.apply(this, arguments), {paid: this.paid,
                                                                              card_number: this.card_number,
                                                                              card_brand: this.card_brand,
                                                                              card_owner_name: this.card_owner_name,
                                                                              ref_no: this.ref_no,
                                                                              record_no: this.record_no,
                                                                              invoice_no: this.invoice_no,
                                                                              mercury_data: this.mercury_data,
                                                                              swipe_pending: this.swipe_pending});
    }
});

// Lookup table to store status and error messages
var lookUpCodeTransaction = {
    'Approved': {
        '000000': _t('Transaction approved'),
    },
    'TimeoutError': {
        '001006': _t('Global API Not Initialized'),
        '001007': _t('Timeout on Response'),
        '003003': _t('Socket Error sending request'),
        '003004': _t('Socket already open or in use'),
        '003005': _t('Socket Creation Failed'),
        '003006': _t('Socket Connection Failed'),
        '003007': _t('Connection Lost'),
        '003008': _t('TCP/IP Failed to Initialize'),
        '003010': _t('Time Out waiting for server response'),
        '003011': _t('Connect Cancelled'),
        '003053': _t('Initialize Failed'),
        '009999': _t('Unknown Error'),
    },
    'FatalError': {
        '-1':     _t('Timeout error'),
        '001001': _t('General Failure'),
        '001003': _t('Invalid Command Format'),
        '001004': _t('Insufficient Fields'),
        '001011': _t('Empty Command String'),
        '002000': _t('Password Verified'),
        '002001': _t('Queue Full'),
        '002002': _t('Password Failed – Disconnecting'),
        '002003': _t('System Going Offline'),
        '002004': _t('Disconnecting Socket'),
        '002006': _t('Refused ‘Max Connections’'),
        '002008': _t('Duplicate Serial Number Detected'),
        '002009': _t('Password Failed (Client / Server)'),
        '002010': _t('Password failed (Challenge / Response)'),
        '002011': _t('Internal Server Error – Call Provider'),
        '003002': _t('In Process with server'),
        '003009': _t('Control failed to find branded serial (password lookup failed)'),
        '003012': _t('128 bit CryptoAPI failed'),
        '003014': _t('Threaded Auth Started Expect Response'),
        '003017': _t('Failed to start Event Thread.'),
        '003050': _t('XML Parse Error'),
        '003051': _t('All Connections Failed'),
        '003052': _t('Server Login Failed'),
        '004001': _t('Global Response Length Error (Too Short)'),
        '004002': _t('Unable to Parse Response from Global (Indistinguishable)'),
        '004003': _t('Global String Error'),
        '004004': _t('Weak Encryption Request Not Supported'),
        '004005': _t('Clear Text Request Not Supported'),
        '004010': _t('Unrecognized Request Format'),
        '004011': _t('Error Occurred While Decrypting Request'),
        '004017': _t('Invalid Check Digit'),
        '004018': _t('Merchant ID Missing'),
        '004019': _t('TStream Type Missing'),
        '004020': _t('Could Not Encrypt Response- Call Provider'),
        '100201': _t('Invalid Transaction Type'),
        '100202': _t('Invalid Operator ID'),
        '100203': _t('Invalid Memo'),
        '100204': _t('Invalid Account Number'),
        '100205': _t('Invalid Expiration Date'),
        '100206': _t('Invalid Authorization Code'),
        '100207': _t('Invalid Authorization Code'),
        '100208': _t('Invalid Authorization Amount'),
        '100209': _t('Invalid Cash Back Amount'),
        '100210': _t('Invalid Gratuity Amount'),
        '100211': _t('Invalid Purchase Amount'),
        '100212': _t('Invalid Magnetic Stripe Data'),
        '100213': _t('Invalid PIN Block Data'),
        '100214': _t('Invalid Derived Key Data'),
        '100215': _t('Invalid State Code'),
        '100216': _t('Invalid Date of Birth'),
        '100217': _t('Invalid Check Type'),
        '100218': _t('Invalid Routing Number'),
        '100219': _t('Invalid TranCode'),
        '100220': _t('Invalid Merchant ID'),
        '100221': _t('Invalid TStream Type'),
        '100222': _t('Invalid Batch Number'),
        '100223': _t('Invalid Batch Item Count'),
        '100224': _t('Invalid MICR Input Type'),
        '100225': _t('Invalid Driver’s License'),
        '100226': _t('Invalid Sequence Number'),
        '100227': _t('Invalid Pass Data'),
        '100228': _t('Invalid Card Type'),
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

gui.define_popup({name:'payment-confirm', widget: PaymentConfirmPopupWidget});
gui.define_popup({name:'payment-transaction', widget: PaymentTransactionPopupWidget});

// On all screens, if a card is swipped, return a popup error.
ScreenWidget.include({
    credit_error_action: function () {
        this.gui.show_popup('error-barcode','Go to payment screen to use cards');
    },

    show: function () {
        this._super();
        if(allowOnlinePayment(this.pos)) {
            this.pos.barcode_reader.set_action_callback('Credit', _.bind(this.credit_error_action, this));
        }
    }
});

// Normally, everything that is tendered is paid. This is not the case
// anymore, because now we can have paymentlines that are waiting for
// a swipe
var _orderproto = pos_model.Order.prototype;
pos_model.Order = pos_model.Order.extend({
    get_due: function(paymentline) {
        var due = 0;
        if (!paymentline) {
            due = this.get_total_with_tax() - this.get_total_paid();
        } else {
            due = this.get_total_with_tax();
            var lines = this.paymentlines.models;
            for (var i = 0; i < lines.length; i++) {
                if (lines[i] === paymentline) {
                    break;
                } else if (! lines[i].swipe_pending) {
                    due -= lines[i].get_amount();
                }
            }
        }
        return round_pr(Math.max(0,due), this.pos.currency.rounding);
    },
    get_total_paid: function() {
        return this.paymentlines.reduce((function(sum, paymentLine) {
            if (! paymentLine.swipe_pending) {
                return sum + paymentLine.get_amount();
            } else {
                return sum;
            }
        }), 0);
    },
});

// On Payment screen, allow electronic payments
PaymentScreenWidget.include({
    _get_swipe_pending_line: function () {
        var i = 0;
        var lines = this.pos.get_order().get_paymentlines();

        for (i = 0; i < lines.length; i++) {
            if (lines[i].swipe_pending) {
                return lines[i];
            }
        }

        return 0;
    },

    _does_credit_payment_line_exist: function (amount, card_number, card_brand, card_owner_name) {
        var i = 0;
        var lines = this.pos.get_order().get_paymentlines();

        for (i = 0; i < lines.length; i++) {
            if (lines[i].amount === amount &&
                lines[i].card_number === card_number &&
                lines[i].card_brand === card_brand &&
                lines[i].card_owner_name === card_owner_name) {
                return true;
            }
        }

        return false;
    },

    retry_credit_code_transaction: function (parsed_result, def, response, retry_nr) {
        var message = "";

        if (! retry_nr) {
            retry_nr = 1;
        }

        if (retry_nr <= 5) {
            if (response) {
                message = "Retry #" + retry_nr + "...<br/><br/>" + response.message;
            } else {
                message = "Retry #" + retry_nr + "...";
            }
            def.notify({
                message: message
            });

            setTimeout(function () {
                self.credit_code_transaction(parsed_result, def, retry_nr + 1);
            }, 1000);
        } else {
            if (response) {
                message = "Error " + response.error + ": " + lookUpCodeTransaction["TimeoutError"][response.error] + " (Mercury down?)<br/>" + response.message;
            } else {
                message = "No response from Mercury (Mercury down?)";
            }
            def.resolve({
                message: message,
                auto_close: false
            });
        }
    },

    // Handler to manage the card reader string
    credit_code_transaction: function (parsed_result, old_deferred, retry_nr) {
        if(!allowOnlinePayment(this.pos)) {
            return;
        }

        var self = this;
        var decodedMagtek = decodeMagtek(parsed_result.code);

        // Construct a dictionary to store all data from the magnetic card
        var transaction = {
            'encrypted_key'     : decodedMagtek['encrypted_key'],
            'encrypted_block'   : decodedMagtek['encrypted_block'],
            'transaction_type'  : 'Credit',
            'transaction_code'  : 'Sale',
            'invoice_no'        : self.pos.get_order().uid.replace(/-/g,''),
            'purchase'          : parsed_result.total,
            'journal_id'        : parsed_result.journal_id,
        };

        var def = old_deferred || new $.Deferred();

        // show the transaction popup.
        // the transaction deferred is used to update transaction status
        // if we have a previous deferred it indicates that this is a retry
        if (! old_deferred) {
            this.gui.show_popup('payment-transaction', {
                transaction: def
            });
            def.notify({
                status: 'Waiting',
                message: 'Handling transaction...',
            });
        }

        var rpc_def = session.rpc("/pos/send_payment_transaction", transaction)
                .done(function (data) {
                    console.log(data); // todo jov

                    // if not receiving a response, we should retry
                    if (data === "timeout") {
                        self.retry_credit_code_transaction(parsed_result, def, null, retry_nr);
                        return;
                    }

                    var response = decodeMercuryResponse(data);
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
                            var swipe_pending_line = self._get_swipe_pending_line();

                            if (swipe_pending_line) {
                                order.select_paymentline(swipe_pending_line);
                            } else {
                                order.add_paymentline(getCashRegisterByJournalID(self.pos.cashregisters, parsed_result.journal_id));
                            }

                            order.selected_paymentline.swipe_pending = false;
                            order.selected_paymentline.paid = true; // todo jov
                            order.selected_paymentline.amount = response.authorize;
                            order.selected_paymentline.card_number = decodedMagtek['number'];
                            order.selected_paymentline.card_brand = response.card_type;
                            order.selected_paymentline.card_owner_name = decodedMagtek['name'];
                            order.selected_paymentline.ref_no = response.ref_no;
                            order.selected_paymentline.record_no = response.record_no;
                            order.selected_paymentline.invoice_no = response.invoice_no;
                            order.selected_paymentline.mercury_data = response; // used to reverse transactions

                            order.selected_paymentline.name =
                                order.selected_paymentline.card_brand + " (****" +
                                order.selected_paymentline.card_number + ")";

                            self.order_changes();
                            self.reset_input();
                            self.render_paymentlines();
                            order.trigger('change', order); // needed so that export_to_JSON gets triggered

                            if (response.message === "PARTIAL AP") {
                                def.resolve({
                                    message: "Partially approved",
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
                            self.retry_credit_code_transaction(parsed_result, def, response, retry_nr);
                        } else { // not recoverable
                            def.resolve({
                                message: "Error " + response.error + ":<br/>" + response.message,
                                auto_close: false
                            });
                        }
                    }

                }).fail(function (data) {
                    def.reject({
                        status: 'Error',
                        error: '-1',
                    });
                });
    },

    credit_code_cancel: function () {
        return;
    },

    credit_code_action: function (parsed_result) {
        self = this;
        parsed_result.total = this.pos.get_order().get_due();

        if (parsed_result.total) {
            if (onlinePaymentJournal.length === 1) {
                parsed_result.journal_id = onlinePaymentJournal[0].item;
                self.credit_code_transaction(parsed_result);
            } else { // this is for supporting another payment system like mercury
                this.gui.show_popup('selection',{
                    title:   'Pay ' + parsed_result.total.toFixed(2) + ' with : ',
                    list:    onlinePaymentJournal,
                    confirm: function (item) {
                        parsed_result.journal_id = item;
                        self.credit_code_transaction(parsed_result);
                    },
                    cancel:  self.credit_code_cancel,
                });
            }
        }
        else {
            var def = new $.Deferred();

            this.gui.show_popup('payment-transaction', {
                transaction: def
            });

            def.resolve({
                "message": "Order is already fully paid."
            });
        }
    },

    do_reversal: function (mercury_data, is_voidsale) {
        var def = new $.Deferred();
        var self = this;

        // show the transaction popup.
        // the transaction deferred is used to update transaction status
        this.gui.show_popup('payment-transaction', {
            transaction: def
        });

        var request_data = _.extend({
            'transaction_type'  : 'Credit',
            'transaction_code'  : 'VoidSaleByRecordNo',
        }, mercury_data);

        var message = "";
        var rpc_url = "/pos/";

        if (is_voidsale) {
            message = "Reversal failed, sending VoidSale...";
            rpc_url += "send_voidsale";
        } else {
            message = "Sending reversal...";
            rpc_url += "send_reversal";
        }

        def.notify({
            error: 0,
            status: 'Waiting',
            message: message,
        });

        session.rpc(rpc_url, request_data)
            .done(function (data) {
                console.log(data); // todo
                var response = decodeMercuryResponse(data);

                if (! is_voidsale) {
                    if (response.status != 'Approved' || response.message != 'REVERSED') {
                        // reversal was not successful, send voidsale
                        self.do_reversal(mercury_data, true);
                    } else {
                        // reversal was successful
                        def.resolve({
                            message: "Reversal succeeded",
                        });
                    }
                } else { // voidsale ended, nothing more we can do
                    if (response.status === 'Approved') {
                        def.resolve({
                            message: "VoidSale succeeded",
                        });
                    } else {
                        def.resolve({
                            message: "Error " + response.error + ":<br/>" + response.message,
                        });
                    }
                }

            })  .fail(function (data) {
                def.reject({
                    status: 'Odoo Error',
                    error: '-1',
                    message: 'Impossible to contact the proxy, please retry ...',
                });
            });
    },

    click_delete_paymentline: function (cid) {
        var lines = this.pos.get_order().get_paymentlines();

        for (var i = 0; i < lines.length; i++) {
            if (lines[i].cid === cid && lines[i].mercury_data) {
                this.do_reversal(lines[i].mercury_data, false);
            }
        }

        this._super(cid);
    },

    // make sure there is only one paymentline waiting for a swipe
    click_paymentmethods: function (id) {
        var i;
        var cashregister = null;
        for (i = 0; i < this.pos.cashregisters.length; i++) {
            if (this.pos.cashregisters[i].journal_id[0] === id){
                cashregister = this.pos.cashregisters[i];
                break;
            }
        }

        if (cashregister.journal.type === 'bank') {
            var already_swipe_pending = false;
            var lines = this.pos.get_order().get_paymentlines();

            for (i = 0; i < lines.length; i++) {
                if (lines[i].cashregister.journal.type === 'bank' && lines[i].swipe_pending) {
                    already_swipe_pending = true;
                }
            }

            if (already_swipe_pending) {
                this.gui.show_popup('error',{
                    'title': 'Error',
                    'body':  'One credit card swipe already pending.',
                });
            } else {
                this._super(id);
                this.pos.get_order().selected_paymentline.swipe_pending = true;
                this.render_paymentlines();
            }
        } else {
            this._super(id);
        }
    },

    show: function () {
        this._super();
        if (allowOnlinePayment(this.pos)) {
            this.pos.barcode_reader.set_action_callback('Credit', _.bind(this.credit_code_action, this));
        }
    }
});

return {
    MagneticParser: BarcodeParser,
    ScreenWidget: ScreenWidget,
};

});
