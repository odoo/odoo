odoo.define('card_reader.MagneticParser', function (require) {
"use strict";

var Class   = require('web.Class');
var Model   = require('web.Model');
var session = require('web.session');
var core    = require('web.core');
var screens = require('point_of_sale.screens');
var gui     = require('point_of_sale.gui');
var pos_model = require('point_of_sale.models');

var Qweb    = core.qweb;
var _t      = core._t;

Qweb.add_template('/card_reader/static/src/xml/templates.xml');

var BarcodeParser = require('barcodes.BarcodeParser');
var PopupWidget = require('point_of_sale.popups');
var ScreenWidget = screens.ScreenWidget;
var PaymentScreenWidget = screens.PaymentScreenWidget;

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


// Extends the payment line object with the "paid" property used to
// know if the payment line is already paid

// the paid parameter is not saved with export as JSON
var _paylineproto = pos_model.Paymentline.prototype;

pos_model.Paymentline = pos_model.Paymentline.extend({
    initialize: function () {
        _paylineproto.initialize.apply(this, arguments);
        this.paid = false;
    },
    init_from_JSON: function (json) {
        this.paid = json.paid;
        _paylineproto.init_from_JSON.apply(this, arguments);
    },
    export_as_JSON: function () {
        return _.extend(_paylineproto.export_as_JSON.apply(this, arguments), {paid: this.paid});
    }
});

// Lookup table to store status and error messages

var lookUpCodeTransaction = {
    'Approved': {
        '000000': _t('Payment Approved'),
    },
    'Declined': {
        '000000': _t('Payment Declined, insufficient balance on your card'),
    },
    'Error': {
        '-1':     _t('Impossible to contact the proxy'),
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
        '001001': _t('General Failure '),
        '004019': _t('TStream Type Missing'),
        '001003': _t('Invalid Command Format '),
        '004020': _t('Could Not Encrypt Response- Call Provider'),
        '001004': _t('Insufficient Fields '),
        '009999': _t('Unknown Error'),
        '001006': _t('Global API Not Initialized '),
        '100201': _t('Invalid Transaction Type'),
        '001007': _t('Timeout on Response '),
        '100202': _t('Invalid Operator ID'),
        '001011': _t('Empty Command String '),
        '100203': _t('Invalid Memo'),
        '003002': _t('In Process with server '),
        '100204': _t('Invalid Account Number'),
        '003003': _t('Socket Error sending request '),
        '100205': _t('Invalid Expiration Date'),
        '003004': _t('Socket already open or in use '),
        '100206': _t('Invalid Authorization Code'),
        '003005': _t('Socket Creation Failed '),
        '100207': _t('Invalid Authorization Code'),
        '003006': _t('Socket Connection Failed '),
        '100208': _t('Invalid Authorization Amount'),
        '003007': _t('Connection Lost '),
        '100209': _t('Invalid Cash Back Amount'),
        '003008': _t('TCP/IP Failed to Initialize '),
        '100210': _t('Invalid Gratuity Amount'),
        '003009': _t('Control failed to find branded serial (password lookup failed)'),
        '100211': _t('Invalid Purchase Amount'),
        '003010': _t('Time Out waiting for server response '),
        '100212': _t('Invalid Magnetic Stripe Data'),
        '003011': _t('Connect Cancelled '),
        '100213': _t('Invalid PIN Block Data'),
        '003012': _t('128 bit CryptoAPI failed '),
        '100214': _t('Invalid Derived Key Data'),
        '003014': _t('Threaded Auth Started Expect Response '),
        '100215': _t('Invalid State Code'),
        '003017': _t('Failed to start Event Thread. '),
        '100216': _t('Invalid Date of Birth'),
        '003050': _t('XML Parse Error '),
        '100217': _t('Invalid Check Type'),
        '003051': _t('All Connections Failed '),
        '100218': _t('Invalid Routing Number'),
        '003052': _t('Server Login Failed '),
        '100219': _t('Invalid TranCode'),
        '003053': _t('Initialize Failed '),
        '100220': _t('Invalid Merchant ID'),
        '004001': _t('Global Response Length Error (Too Short) '),
        '100221': _t('Invalid TStream Type'),
        '004002': _t('Unable to Parse Response from Global (Indistinguishable)'),
        '100222': _t('Invalid Batch Number'),
        '004003': _t('Global String Error '),
        '100223': _t('Invalid Batch Item Count'),
        '004004': _t('Weak Encryption Request Not Supported '),
        '100224': _t('Invalid MICR Input Type'),
        '004005': _t('Clear Text Request Not Supported '),
        '100225': _t('Invalid Driver’s License'),
        '004010': _t('Unrecognized Request Format '),
        '100226': _t('Invalid Sequence Number'),
        '004011': _t('Error Occurred While Decrypting Request '),
        '100227': _t('Invalid Pass Data'),
        '004017': _t('Invalid Check Digit '),
        '100228': _t('Invalid Card Type'),
        '004018': _t('Merchant ID Missing'),
    },
};

// Popup to show all transaction state for the payment.

var PaymentTransactionPopupWidget = PopupWidget.extend({
    template: 'PaymentTransactionPopupWidget',
    show: function (options) {
        var self = this;
        this._super(options);
        options.transaction.then(function (data) {
            // if the status and error code are known, use our custom message from the lookup table
            if (!(!lookUpCodeTransaction[data.status] || !lookUpCodeTransaction[data.status][data.error])) {
                data.message = lookUpCodeTransaction[data.status][data.error];
            }

            data.error = (data.error != '000000') ? ' '+data.error : '';
            self.$el.find('p.body').html(data.status+' '+data.error+'<br /><br />'+data.message);

            // If an error occure, allow user to close the popup
            if(data.status != 'Approved') {
                self.close();
                self.$el.find('.popup').append('<div class="footer"><div class="button cancel">Ok</div></div>');
            }
            // Else autoclose the popup
            else {
                setTimeout(function () {
                    self.close();
                    self.hide();
                }, 2000);
            }

        }).progress(function (data) {
            data.error = (data.error != '000000') ? ' '+data.error : '';
            self.$el.find('p.body').html(data.status+' '+data.error+'<br /><br />'+data.message);
        });
    }
});

gui.define_popup({name:'payment-confirm', widget: PaymentConfirmPopupWidget});
gui.define_popup({name:'payment-transaction', widget: PaymentTransactionPopupWidget});

BarcodeParser.include({
    // returns true if the magnetic code string is encoded with the provided encoding.
    check_encoding: function(barcode, encoding) {
        if(!this._super(barcode, encoding)) {
            if(encoding === 'magnetic_credit') {
                return (barcode[0] == '%'); // need a better test to avoid errors
            } else {
                return false;
            }
        } else {
            return true;
        }
    }
});

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

// On Payment screen, allow electronic payments
PaymentScreenWidget.include({
    // Regular expression to identify and extract data from the track 1 & 2 of the magnetic code
    _track1:/%B?([0-9]*)\^([A-Z\/ -_]*)\^([0-9]{4})(.{3})([^?]+)\?/,
    _track2:/\;([0-9]+)=([0-9]{4})(.{3})([^?]+)\?/,

    // Extract data from a track list to a track dictionnary
    _decode_track: function(track_list) {

        if(track_list < 6) return {};

        return {
            'private'       : track_list.pop(),
            'service_code'  : track_list.pop(),
            'validity'      : track_list.pop(),
            'name'          : track_list.pop(),
            'card_number'   : track_list.pop(),
            'original'      : track_list.pop(),
        };

    },
    // Extract data from crypted track list to a track dictionnary
    _decode_encrypted_data: function (code_list) {
        if(code_list < 13) return {};
        var encrypted_data = {
            'format_code'           : code_list.pop(),
            'enc_crc'               : code_list.pop(),
            'clear_text_crc'        : code_list.pop(),
        };

        if(code_list.lenght > 10) {
            encrypted_data['encryption_counter'] = code_list.pop();
        }

        _.extend(encrypted_data, {
            'dukpt_serial_n'        : code_list.pop(),
            'enc_session_id'        : code_list.pop(),
            'device_serial'         : code_list.pop(),
            'magneprint_data'       : code_list.pop(),
            'magneprint_status'     : code_list.pop(),
            'enc_track3'            : code_list.pop(),
            'enc_track2'            : code_list.pop(),
            'enc_track1'            : code_list.pop(),
            'reader_enc_status'     : code_list.pop(),
        });
        return encrypted_data;
    },

    // Handler to manage the card reader string
    credit_code_transaction: function (parsed_result) {
        if(!allowOnlinePayment(this.pos)) {
            return;
        }

        var def = new $.Deferred();
        var self = this;

        // show the transaction popup.
        // the transaction deferred is used to update transaction status
        this.gui.show_popup('payment-transaction', {
            transaction: def
        });

        // Construct a dictionnary to store all data from the magnetic card
        var transaction = {
            track1: this._decode_track(parsed_result.code.match(this._track1)),
            track2: this._decode_track(parsed_result.code.match(this._track2)),
            track3: {},
            encrypted_data: this._decode_encrypted_data(parsed_result.code.split('|')),
        };

        // Extends the dictionnary with needed client side data to complete the request transaction

        _.extend(transaction, {
            'transaction_type'  : 'Credit',
            'transaction_code'  : 'Sale',
            'invoice_no'        : 'SLK423K',
            'amount'            : parsed_result.total,
            'action'            : 'CreditTransaction',
            'journal_id'        : parsed_result.journal_id,
        });

        def.notify({
            error: 0,
            status: 'Waiting',
            message: 'Sending transaction to payment support ...',
        });

        session.rpc("/pos/send_payment_transaction", transaction)
            .done(function (data) {
                console.log(data);
                // Decode the response of the payment server
                var status  = data.match(/&lt;CmdStatus&gt;(.*)&lt;\/CmdStatus&gt;/)[1];
                var error   = data.match(/&lt;DSIXReturnCode&gt;(.*)&lt;\/DSIXReturnCode&gt;/)[1];
                var message = data.match(/&lt;TextResponse&gt;(.*)&lt;\/TextResponse&gt;/)[1];
                var amount  = data.match(/&lt;Authorize&gt;(.*)&lt;\/Authorize&gt;/)[1];

                if (status === 'Approved') {
                    // If the payment is approved, add a payment line and try to close the order
                    var order = self.pos.get_order();
                    order.add_paymentline(getCashRegisterByJournalID(self.pos.cashregisters, parsed_result.journal_id));
                    order.selected_paymentline.paid = true;
                    order.selected_paymentline.amount = amount;
                    self.reset_input();
                    self.render_paymentlines();
                    setTimeout(_.bind(self.validate_order, self), 3000);
                }

                def.resolve({
                    status: status,
                    error: error,
                    message: message,
                });


        })  .fail(function (data) {
                def.reject({
                    status: 'Odoo Error',
                    error: '-1',
                    message: 'Impossible to contact the proxy, please retry ...',
                });
        });
    },
    credit_code_cancel: function () {
        return;
    },

    credit_code_action: function (parsed_result) {
        self = this;
        parsed_result.total = this.pos.get_order().get_due().toFixed(2);

        if (parsed_result.total) {

            this.gui.show_popup('selection',{
                title:   'Pay ' + parsed_result.total + ' with : ',
                list:    onlinePaymentJournal,
                confirm: function (item) {
                    parsed_result.journal_id = item;
                    self.credit_code_transaction(parsed_result);
                },
                cancel:  self.credit_code_cancel,
                total:   parsed_result.total,
            });
        }
        else {
            // display error popup
        }
    },

    show: function () {
        this._super();
        if (allowOnlinePayment(this.pos)) {
            this.pos.barcode_reader.set_action_callback('Credit', _.bind(this.credit_code_action, this));
        }
    }
});

window.test_card_reader = {
    MagneticParser: BarcodeParser,
    ScreenWidget: ScreenWidget,
    QWeb : Qweb,
};

return {
    MagneticParser: BarcodeParser,
    ScreenWidget: ScreenWidget,
};

});
