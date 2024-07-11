/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { useBarcodeReader } from "@point_of_sale/app/barcode/barcode_reader_hook";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { PaymentTransactionPopup } from "@pos_mercury/app/payment_transaction_popup/payment_transaction_popup";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";

// Lookup table to store status and error messages
const lookUpCodeTransaction = {
    Approved: {
        "000000": _t("Transaction approved"),
    },
    TimeoutError: {
        "001006": "Global API Not Initialized",
        "001007": "Timeout on Response",
        "003003": "Socket Error sending request",
        "003004": "Socket already open or in use",
        "003005": "Socket Creation Failed",
        "003006": "Socket Connection Failed",
        "003007": "Connection Lost",
        "003008": "TCP/IP Failed to Initialize",
        "003010": "Time Out waiting for server response",
        "003011": "Connect Canceled",
        "003053": "Initialize Failed",
        "009999": "Unknown Error",
    },
    FatalError: {
        "-1": "Timeout error",
        "001001": "General Failure",
        "001003": "Invalid Command Format",
        "001004": "Insufficient Fields",
        "001011": "Empty Command String",
        "002000": "Password Verified",
        "002001": "Queue Full",
        "002002": "Password Failed – Disconnecting",
        "002003": "System Going Offline",
        "002004": "Disconnecting Socket",
        "002006": "Refused ‘Max Connections’",
        "002008": "Duplicate Serial Number Detected",
        "002009": "Password Failed (Client / Server)",
        "002010": "Password failed (Challenge / Response)",
        "002011": "Internal Server Error – Call Provider",
        "003002": "In Process with server",
        "003009": "Control failed to find branded serial (password lookup failed)",
        "003012": "128 bit CryptoAPI failed",
        "003014": "Threaded Auth Started Expect Response",
        "003017": "Failed to start Event Thread.",
        "003050": "XML Parse Error",
        "003051": "All Connections Failed",
        "003052": "Server Login Failed",
        "004001": "Global Response Length Error (Too Short)",
        "004002": "Unable to Parse Response from Global (Indistinguishable)",
        "004003": "Global String Error",
        "004004": "Weak Encryption Request Not Supported",
        "004005": "Clear Text Request Not Supported",
        "004010": "Unrecognized Request Format",
        "004011": "Error Occurred While Decrypting Request",
        "004017": "Invalid Check Digit",
        "004018": "Merchant ID Missing",
        "004019": "TStream Type Missing",
        "004020": "Could Not Encrypt Response- Call Provider",
        100201: "Invalid Transaction Type",
        100202: "Invalid Operator ID",
        100203: "Invalid Memo",
        100204: "Invalid Account Number",
        100205: "Invalid Expiration Date",
        100206: "Invalid Authorization Code",
        100207: "Invalid Authorization Code",
        100208: "Invalid Authorization Amount",
        100209: "Invalid Cash Back Amount",
        100210: "Invalid Gratuity Amount",
        100211: "Invalid Purchase Amount",
        100212: "Invalid Magnetic Stripe Data",
        100213: "Invalid PIN Block Data",
        100214: "Invalid Derived Key Data",
        100215: "Invalid State Code",
        100216: "Invalid Date of Birth",
        100217: "Invalid Check Type",
        100218: "Invalid Routing Number",
        100219: "Invalid TranCode",
        100220: "Invalid Merchant ID",
        100221: "Invalid TStream Type",
        100222: "Invalid Batch Number",
        100223: "Invalid Batch Item Count",
        100224: "Invalid MICR Input Type",
        100225: "Invalid Driver’s License",
        100226: "Invalid Sequence Number",
        100227: "Invalid Pass Data",
        100228: "Invalid Card Type",
    },
};

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.pos.getOnlinePaymentMethods().length !== 0) {
            useBarcodeReader({
                credit: this.credit_code_action,
            });
        }
        // How long we wait for the odoo server to deliver the response of
        // a Vantiv transaction
        this.server_timeout_in_ms = 95000;

        // How many Vantiv transactions we send without receiving a
        // response
        this.server_retries = 3;
    },
    /**
     * The card reader acts as a barcode scanner. This sets up
     * the numberBuffer to not immediately act on keyboard
     * input.
     *
     * @override
     */
    get _getNumberBufferConfig() {
        const res = super._getNumberBufferConfig;
        res["useWithBarcode"] = true;
        return res;
    },
    _get_swipe_pending_line() {
        var i = 0;
        var lines = this.pos.get_order().get_paymentlines();

        for (i = 0; i < lines.length; i++) {
            if (lines[i].mercury_swipe_pending) {
                return lines[i];
            }
        }

        return 0;
    },
    _does_credit_payment_line_exist(amount, card_number, card_brand, card_owner_name) {
        var i = 0;
        var lines = this.pos.get_order().get_paymentlines();

        for (i = 0; i < lines.length; i++) {
            if (
                lines[i].mercury_amount === amount &&
                lines[i].mercury_card_number === card_number &&
                lines[i].mercury_card_brand === card_brand &&
                lines[i].mercury_card_owner_name === card_owner_name
            ) {
                return true;
            }
        }

        return false;
    },
    retry_mercury_transaction(def, response, retry_nr, can_connect_to_server, callback, args) {
        var self = this;
        var message = "";

        if (retry_nr < self.server_retries) {
            if (response) {
                message = "Retry #" + (retry_nr + 1) + "...<br/><br/>" + response.message;
            } else {
                message = "Retry #" + (retry_nr + 1) + "...";
            }
            def.notify({
                message: message,
            });

            setTimeout(function () {
                callback.apply(self, args);
            }, 1000);
        } else {
            if (response) {
                message =
                    "Error " +
                    response.error +
                    ": " +
                    lookUpCodeTransaction["TimeoutError"][response.error] +
                    "<br/>" +
                    response.message;
            } else {
                if (can_connect_to_server) {
                    message = _t("No response from Vantiv (Vantiv down?)");
                } else {
                    message = _t("No response from server (connected to network?)");
                }
            }
            def.resolve({
                message: message,
                auto_close: false,
            });
        }
    },
    // Handler to manage the card reader string
    credit_code_transaction(parsed_result, old_deferred, retry_nr) {
        const order = this.pos.get_order();
        if (order.get_due(order.selected_paymentline) < 0) {
            this.popup.add(ErrorPopup, {
                title: _t("Refunds not supported"),
                body: _t(
                    "Credit card refunds are not supported. Instead select your credit card payment method, click 'Validate' and refund the original charge manually through the Vantiv backend."
                ),
            });
            return;
        }

        if (this.pos.getOnlinePaymentMethods().length === 0) {
            return;
        }

        var decodedMagtek = this.pos.decodeMagtek(parsed_result.code);

        if (!decodedMagtek) {
            this.popup.add(ErrorPopup, {
                title: _t("Could not read card"),
                body: _t(
                    "This can be caused by a badly executed swipe or by not having your keyboard layout set to US QWERTY (not US International)."
                ),
            });
            return;
        }

        var swipe_pending_line = this._get_swipe_pending_line();
        var purchase_amount = 0;

        if (swipe_pending_line) {
            purchase_amount = swipe_pending_line.get_amount();
        } else {
            purchase_amount = this.pos.get_order().get_due();
        }

        var transaction = {
            encrypted_key: decodedMagtek["encrypted_key"],
            encrypted_block: decodedMagtek["encrypted_block"],
            transaction_type: "Credit",
            transaction_code: "Sale",
            invoice_no: this.pos.get_order().uid.replace(/-/g, ""),
            purchase: purchase_amount,
            payment_method_id: parsed_result.payment_method_id,
        };

        var def = old_deferred || new $.Deferred();
        retry_nr = retry_nr || 0;

        // show the transaction popup.
        // the transaction deferred is used to update transaction status
        // if we have a previous deferred it indicates that this is a retry
        if (!old_deferred) {
            this.popup.add(PaymentTransactionPopup, {
                transaction: def,
            });
            def.notify({
                message: _t("Handling transaction..."),
            });
        }
        // FIXME POSREF timeout
        this.orm
            .call("pos_mercury.mercury_transaction", "do_payment", [transaction])
            .then((data) => {
                // if not receiving a response from Vantiv, we should retry
                if (data === "timeout") {
                    this.retry_mercury_transaction(
                        def,
                        null,
                        retry_nr,
                        true,
                        this.credit_code_transaction,
                        [parsed_result, def, retry_nr + 1]
                    );
                    return;
                }

                if (data === "not setup") {
                    def.resolve({
                        message: _t("Please setup your Vantiv merchant account."),
                    });
                    return;
                }

                if (data === "internal error") {
                    def.resolve({
                        message: _t("Odoo error while processing transaction."),
                    });
                    return;
                }

                var response = this.pos.decodeMercuryResponse(data);
                response.payment_method_id = parsed_result.payment_method_id;

                if (response.status === "Approved") {
                    // AP* indicates a duplicate request, so don't add anything for those
                    if (
                        response.message === "AP*" &&
                        this._does_credit_payment_line_exist(
                            response.authorize,
                            decodedMagtek["number"],
                            response.card_type,
                            decodedMagtek["name"]
                        )
                    ) {
                        def.resolve({
                            message: lookUpCodeTransaction["Approved"][response.error],
                            auto_close: true,
                        });
                    } else {
                        // If the payment is approved, add a payment line
                        var order = this.pos.get_order();

                        if (swipe_pending_line) {
                            order.select_paymentline(swipe_pending_line);
                        } else {
                            order.add_paymentline(
                                this.payment_methods_by_id[parsed_result.payment_method_id]
                            );
                        }

                        order.selected_paymentline.paid = true;
                        order.selected_paymentline.mercury_swipe_pending = false;
                        order.selected_paymentline.mercury_amount = response.authorize;
                        order.selected_paymentline.set_amount(response.authorize);
                        order.selected_paymentline.mercury_card_number = decodedMagtek["number"];
                        order.selected_paymentline.mercury_card_brand = response.card_type;
                        order.selected_paymentline.mercury_card_owner_name = decodedMagtek["name"];
                        order.selected_paymentline.mercury_ref_no = response.ref_no;
                        order.selected_paymentline.mercury_record_no = response.record_no;
                        order.selected_paymentline.mercury_invoice_no = response.invoice_no;
                        order.selected_paymentline.mercury_auth_code = response.auth_code;
                        order.selected_paymentline.mercury_data = response; // used to reverse transactions
                        order.selected_paymentline.set_credit_card_name();

                        this.numberBuffer.reset();

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
                    if (lookUpCodeTransaction["TimeoutError"][response.error]) {
                        // recoverable error
                        this.retry_mercury_transaction(
                            def,
                            response,
                            retry_nr,
                            true,
                            this.credit_code_transaction,
                            [parsed_result, def, retry_nr + 1]
                        );
                    } else {
                        // not recoverable
                        def.resolve({
                            message: "Error " + response.error + ":<br/>" + response.message,
                            auto_close: false,
                        });
                    }
                }
            })
            .catch(() => {
                this.retry_mercury_transaction(
                    def,
                    null,
                    retry_nr,
                    false,
                    this.credit_code_transaction,
                    [parsed_result, def, retry_nr + 1]
                );
            });
    },
    credit_code_cancel() {
        return;
    },
    credit_code_action(parsed_result) {
        var online_payment_methods = this.pos.getOnlinePaymentMethods();

        if (online_payment_methods.length === 1) {
            parsed_result.payment_method_id = online_payment_methods[0].item;
            this.credit_code_transaction(parsed_result);
        } else {
            // this is for supporting another payment system like mercury
            const selectionList = online_payment_methods.map((paymentMethod) => ({
                id: paymentMethod.item,
                label: paymentMethod.label,
                isSelected: false,
                item: paymentMethod.item,
            }));
            this.popup
                .add(SelectionPopup, {
                    title: _t("Pay with: "),
                    list: selectionList,
                })
                .then(({ confirmed, payload: selectedPaymentMethod }) => {
                    if (confirmed) {
                        parsed_result.payment_method_id = selectedPaymentMethod;
                        this.credit_code_transaction(parsed_result);
                    } else {
                        this.credit_code_cancel();
                    }
                });
        }
    },
    remove_paymentline_by_ref(line) {
        this.pos.get_order().remove_paymentline(line);
        this.numberBuffer.reset();
    },
    do_reversal(line, is_voidsale, old_deferred, retry_nr) {
        var def = old_deferred || new $.Deferred();
        var self = this;
        retry_nr = retry_nr || 0;

        // show the transaction popup.
        // the transaction deferred is used to update transaction status
        this.popup.add(PaymentTransactionPopup, {
            transaction: def,
        });

        var request_data = Object.assign(
            {
                transaction_type: "Credit",
                transaction_code: "VoidSaleByRecordNo",
            },
            line.mercury_data
        );

        var message = "";
        var rpc_method = "";

        if (is_voidsale) {
            message = _t("Reversal failed, sending VoidSale...");
            rpc_method = "do_voidsale";
        } else {
            message = _t("Sending reversal...");
            rpc_method = "do_reversal";
        }

        if (!old_deferred) {
            def.notify({
                message: message,
            });
        }
        // FIXME POSREF timeout
        this.orm
            .call("pos_mercury.mercury_transaction", rpc_method, [request_data])
            .then(function (data) {
                if (data === "timeout") {
                    self.retry_mercury_transaction(def, null, retry_nr, true, self.do_reversal, [
                        line,
                        is_voidsale,
                        def,
                        retry_nr + 1,
                    ]);
                    return;
                }

                if (data === "internal error") {
                    def.resolve({
                        message: _t("Odoo error while processing transaction."),
                    });
                    return;
                }

                var response = self.pos.decodeMercuryResponse(data);

                if (!is_voidsale) {
                    if (response.status != "Approved" || response.message != "REVERSED") {
                        // reversal was not successful, send voidsale
                        self.do_reversal(line, true);
                    } else {
                        // reversal was successful
                        def.resolve({
                            message: _t("Reversal succeeded"),
                        });

                        self.remove_paymentline_by_ref(line);
                    }
                } else {
                    // voidsale ended, nothing more we can do
                    if (response.status === "Approved") {
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
            })
            .catch(function () {
                self.retry_mercury_transaction(def, null, retry_nr, false, self.do_reversal, [
                    line,
                    is_voidsale,
                    def,
                    retry_nr + 1,
                ]);
            });
    },
    /**
     * @override
     */
    deletePaymentLine(cid) {
        const line = this.paymentLines.find((line) => line.cid === cid);
        if (line.mercury_data) {
            this.do_reversal(line, false);
        } else {
            super.deletePaymentLine(cid);
        }
    },
    /**
     * @override
     */
    addNewPaymentLine(paymentMethod) {
        const order = this.pos.get_order();
        const res = super.addNewPaymentLine(...arguments);
        if (res && paymentMethod.pos_mercury_config_id) {
            order.selected_paymentline.mercury_swipe_pending = true;
        }
    },
});
