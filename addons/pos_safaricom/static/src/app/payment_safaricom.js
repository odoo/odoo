import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";
import { TextInputPopup } from "@point_of_sale/app/components/popups/text_input_popup/text_input_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { MpesaTransactionPopup } from "@pos_safaricom/app/components/popups/mpesa_transaction_popup";

export class PaymentSafaricom extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.paymentLineResolvers = {};
    }

    sendPaymentRequest(uuid) {
        super.sendPaymentRequest(uuid);
        if (this.payment_method_id.safaricom_payment_type == "mpesa_express") {
            return this._mpesa_express_pay(uuid);
        } else {
            return this._lipa_na_mpesa_pay(uuid);
        }
    }

    _call_safaricom(data, action) {
        if (data) {
            return this.env.services.orm.silent.call("pos.payment.method", action, [
                [this.payment_method_id.id],
                data,
            ]);
        }
    }

    _safaricom_handle_response(response, paymentLine) {
        if (response.error && response.error !== "Success") {
            this._show_error(response.error);
            paymentLine.setPaymentStatus("retry");
            return false;
        }
        paymentLine.uiState = paymentLine.uiState || {};
        // Store the IDs from Safaricom for matching with callback
        if (response.checkout_request_id) {
            paymentLine.uiState.safaricom_checkout_request_id = response.checkout_request_id;
        }
        if (response.merchant_request_id) {
            paymentLine.uiState.safaricom_merchant_request_id = response.merchant_request_id;
        }
        return this.waitForPaymentConfirmation(paymentLine);
    }

    async _mpesa_express_pay(uuid) {
        const order = this.pos.getOrder();
        const line = order.payment_ids.find((paymentLine) => paymentLine.uuid === uuid);

        if (!this._validatePaymentLine(line)) {
            return Promise.resolve(false);
        }

        // Get default phone number from customer if available
        const defaultPhone = order.partner?.phone || "";

        // Prompt user to enter phone number
        const phoneNumber = await makeAwaitable(this.env.services.dialog, TextInputPopup, {
            title: _t("M-Pesa Phone Number"),
            placeholder: "254712345678",
            startingValue: defaultPhone,
        });

        if (!phoneNumber) {
            this._show_error(_t("Phone number is required for M-Pesa payment."));
            return Promise.resolve(false);
        }

        line.setPaymentStatus("waitingCard");

        const data = {
            amount: Math.round(line.amount),
            phone_number: phoneNumber,
            account_reference: order.name || order.uuid,
            transaction_desc: `Payment for ${order.name || "Order"}`,
            checkout_request_id: line.uuid,
        };

        return this._call_safaricom(data, "mpesa_express_send_payment_request").then((data) =>
            this._safaricom_handle_response(data, line)
        );
    }

    waitForPaymentConfirmation(paymentLine) {
        return new Promise((resolve) => {
            // Store resolver to be called from callback
            this.paymentLineResolvers[paymentLine.uuid] = resolve;
        });
    }

    // Method to complete payment from callback
    completePayment(paymentLine, success) {
        const resolver = this.paymentLineResolvers[paymentLine.uuid];
        if (resolver) {
            delete this.paymentLineResolvers[paymentLine.uuid];
            resolver(success);
        }
    }

    isPaymentSuccessful(notification) {
        return notification && notification.success === true;
    }

    handleSuccessResponse(line, notification) {
        line.transaction_id = notification.transaction_id;
        line.card_type = "M-Pesa";
        if (notification.phone_number) {
            line.cardholder_name = notification.phone_number;
        }
    }

    _show_error(msg, title) {
        if (!title) {
            title = _t("Safaricom M-Pesa Error");
        }
        this.env.services.dialog.add(AlertDialog, {
            title: title,
            body: msg,
        });
    }

    _validatePaymentLine(line) {
        if (!line) {
            this._show_error(_t("Payment line not found"));
            return false;
        }

        if (line.amount < 0) {
            this._show_error(_t("Cannot process transactions with negative amount."));
            return false;
        }

        if (!Number.isInteger(line.amount)) {
            this._show_error(
                _t("Cannot process transactions with float numbers. Round it please.")
            );
            return false;
        }

        return true;
    }

    async _lipa_na_mpesa_pay(uuid) {
        const order = this.pos.getOrder();
        const line = order.payment_ids.find((paymentLine) => paymentLine.uuid === uuid);

        if (!this._validatePaymentLine(line)) {
            return Promise.resolve(false);
        }

        line.setPaymentStatus("waitingCard");

        const qrData = {
            ref: order.uuid,
            amount: line.amount.toString(),
        };
        const qrCode = await this._call_safaricom(qrData, "generate_qr_code");

        if (!qrCode || qrCode.error) {
            this._show_error(qrCode?.error || _t("Failed to generate QR code"));
            line.setPaymentStatus("retry");
            return false;
        }

        // Set QR payment data for customer display
        line.qrPaymentData = {
            name: this.payment_method_id.name,
            amount: this.pos.env.utils.formatCurrency(line.amount),
            qrCode: "data:image/png;base64," + qrCode,
        };

        // Update customer display to show the QR code
        if (this.pos.customerDisplay) {
            this.pos.customerDisplay.update();
        }

        try {
            const transaction = await makeAwaitable(
                this.env.services.dialog,
                MpesaTransactionPopup,
                {
                    qrCode: qrCode,
                }
            );

            if (!transaction) {
                line.setPaymentStatus("retry");
                return false;
            }
            line.setAmount(transaction.amount);
            line.transaction_id = transaction.id;
            line.card_type = "M-Pesa";
            line.cardholder_name = transaction.phone;
            line.setPaymentStatus("done");

            // Mark transaction as used by deleting it from the database
            await this._call_safaricom(transaction.id, "mark_transaction_used");

            return true;
        } finally {
            // Clear QR payment data from customer display
            line.qrPaymentData = null;
            if (this.pos.customerDisplay) {
                this.pos.customerDisplay.update();
            }
        }
    }
}

register_payment_method("safaricom", PaymentSafaricom);
