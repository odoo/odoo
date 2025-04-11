import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import * as kpay from "@pos_kpay/app/kpay";

export class PaymentKpay extends PaymentInterface {
    setup() {
        super.setup(...arguments);

        const settings = new kpay.KpaySettings();
        settings.endpoint = this.payment_method_id.kpay_terminal_endpoint;
        settings.appId = this.payment_method_id.kpay_app_id;
        settings.appSecret = this.payment_method_id.kpay_app_secret;

        this.terminal = new kpay.KpayTerminal(settings);
        this._kpay_sign(true);
        this.paymentLineResolvers = {};
    }

    send_payment_request(uuid) {
        super.send_payment_request(...arguments);
        return this._kpay_pay(uuid);
    }

    send_payment_cancel(order, uuid) {
        super.send_payment_cancel(order, uuid);
        return this._kpay_cancel();
    }

    pending_kpay_line() {
        return this.pos.getPendingPaymentLine("kpay");
    }

    _handle_connection_failure(data = {}) {
        const line = this.pending_kpay_line();
        if (line) {
            line.set_payment_status("retry");
        }
        console.error("KPay connection error: ", data);
        this._showError(_t("Connection to KPay failed"));

        return false;
    }
    _generate_terminal_request_id() {
        this.terminalRequestId = Math.random().toString(36).substring(2, 12);
        return this.terminalRequestId;
    }

    _kpay_sign(ignore_error = false) {
        return this.terminal.sign(ignore_error).then((data) => {
            if (!data) {
                this._handle_connection_failure();
                return false;
            }
            this.pos.data.silentCall("pos.payment.method", "kpay_set_public_key", [
                [this.payment_method_id.id],
                `-----BEGIN PUBLIC KEY-----\n${data.platformPublicKey}\n-----END PUBLIC KEY-----`,
            ]);
        });
    }

    _kpay_pay(uuid) {
        const order = this.pos.get_order();
        this.terminalRequestId++;

        if (order.get_selected_paymentline().amount <= 0) {
            this._showError(_t("Cannot process transactions with negative amount."));
            return Promise.resolve();
        }

        const rounding = this.pos.currency.rounding;
        const payAmount = Math.round(order.get_selected_paymentline().amount / rounding);
        const tipsAmount = Math.round(order.get_tip() / rounding);
        const payload = {
            includeReceipt: true,
            outTradeNo: order.pos_reference + "-" + this._generate_terminal_request_id(),
            payAmount: String(payAmount).padStart(12, "0"),
            tipsAmount: String(tipsAmount).padStart(12, "0"),
            payCurrency: order.currency.iso_numeric.toString(),
            callbackUrl: `${this.pos.session._base_url}/pos_kpay/${this.payment_method_id.kpay_app_id}/notification`,
        };
        if (this.payment_method_id.kpay_payment_type) {
            payload.paymentType = this.payment_method_id.kpay_payment_type;
            payload.callbackUrl = `${this.pos.session._base_url}/pos_kpay/${this.payment_method_id.kpay_app_id}-${this.payment_method_id.kpay_payment_type}/notification`;
        }

        return this.terminal
            .sales(payload)
            .then((data) => {
                return this._kpay_handle_response(data);
            })
            .catch(this._handle_connection_failure.bind(this));
    }

    _kpay_cancel() {
        const order = this.pos.get_order();
        return this.terminal.close({
            outTradeNo: order.pos_reference + "-" + this.terminalRequestId,
        });
    }

    _kpay_handle_response(result) {
        const line = this.pending_kpay_line();

        if (result.code !== 10000) {
            console.error("error from KPay: ", result);

            this._showError(
                _t("An unexpected error occurred. Message from KPay: ") + result.message
            );
            if (line) {
                line.set_payment_status("force_done");
            }
            return false;
        } else {
            line.set_payment_status("waitingCard");
            return this.waitForPaymentConfirmation();
        }
    }

    waitForPaymentConfirmation() {
        return new Promise((resolve) => {
            this.paymentLineResolvers[this.pending_kpay_line().uuid] = resolve;
        });
    }

    async handleKpayStatusResponse() {
        const notification = await this.pos.data.silentCall(
            "pos.payment.method",
            "get_latest_kpay_status",
            [[this.payment_method_id.id]]
        );
        if (!notification) {
            this._handle_connection_failure();
            return;
        }
        const line = this.pending_kpay_line();
        const isPaymentSuccessful = notification.payResult === 2;

        if (isPaymentSuccessful && line) {
            this.handleSuccessResponse(line, notification);
        }

        const resolver = line ? this.paymentLineResolvers?.[line.uuid] : null;
        if (resolver) {
            resolver(isPaymentSuccessful);
        } else if (line) {
            line.handle_payment_response(isPaymentSuccessful);
        }
    }

    handleSuccessResponse(line, notification) {
        const isCreditCard = Boolean(notification.refNo);
        line.payment_method_payment_mode = kpay.PAYMENT_METHODS_MAPPING[notification.payMethod];

        if (isCreditCard) {
            line.transaction_id = notification.refNo;
            line.card_brand = notification.aidLabel;
            line.card_no = (notification.cardNo && notification.cardNo.slice(-4)) || "";
        } else {
            line.transaction_id = notification.transactionNo;
        }
        this.terminalRequestId = 0;
    }

    _showError(msg, title) {
        if (!title) {
            title = _t("KPay Error");
        }
        this.env.services.dialog.add(AlertDialog, {
            title: title,
            body: msg,
        });
    }
}

register_payment_method("kpay", PaymentKpay);
