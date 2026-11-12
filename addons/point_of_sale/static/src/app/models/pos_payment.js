import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { sortBy } from "@web/core/utils/arrays";
import { generateQRCodeDataUrl } from "@point_of_sale/utils";
const { DateTime } = luxon;

export class PosPayment extends Base {
    static pythonModel = "pos.payment";

    setup(vals) {
        super.setup(...arguments);
        if (!this.payment_date) {
            this.payment_date = DateTime.now();
        }
        this.amount = vals.amount || 0;
        this.ticket = vals.ticket || "";
    }

    initState() {
        super.initState();
        this.uiState = { initStateDate: DateTime.now() };
    }

    get config() {
        return this.models["pos.config"].get(odoo.pos_config_id);
    }

    get currency() {
        return this.foreign_currency_id || this.pos_order_id.currency;
    }

    get isDifferentCurrency() {
        return (
            this.foreign_currency_id &&
            this.foreign_currency_id.id !== this.pos_order_id.currency.id
        );
    }

    getQrPopupProps() {
        return {
            qrCode: this.qr_code,
            amount: formatCurrency(this.amount_currency || this.getAmount(), this.currency),
            provider: this.payment_provider,
        };
    }

    /**
     * Kept in snake_case for consistency with existing model fields.
     * @returns {import("@pos_payment_method/payment_method").PaymentMethod}
     */
    get payment_interface() {
        return this.payment_method_id.payment_interface;
    }

    /**
     * Kept in snake_case for consistency with existing model fields.
     */
    get payment_provider() {
        return this.payment_method_id.payment_provider;
    }

    get useTerminal() {
        return this.payment_method_id.useTerminal;
    }

    get useCashMachine() {
        return this.payment_method_id.useCashMachine;
    }

    get useQr() {
        return this.payment_method_id.useQr;
    }

    get displayName() {
        return this.payment_method_id.name;
    }

    isSelected() {
        return this.pos_order_id?.uiState?.selected_paymentline_uuid === this.uuid;
    }

    setAmount(value, currency = this.pos_order_id.currency) {
        this.pos_order_id.assertEditable();
        const orderCurrency = this.pos_order_id.currency;

        if (currency.id !== orderCurrency.id) {
            this.amount_currency = parseFloat(value) || 0;
            const amountInCompanyCurrency = this.currency.convertToDefaultCurrency(
                this.amount_currency
            );
            this.amount = orderCurrency.round(orderCurrency.convert(amountInCompanyCurrency));
        } else {
            this.amount = orderCurrency.round(parseFloat(value) || 0);
            this.amount_currency = this.pos_order_id.convertAmountToCurrency(
                this.amount,
                this.currency
            );
        }
    }

    getAmount() {
        return this.amount || 0;
    }

    getPaymentStatus() {
        return this.payment_status;
    }

    setPaymentStatus(value) {
        this.payment_status = value;
    }

    isDone() {
        const status = this.getPaymentStatus();
        return status ? status === "done" : true;
    }

    isProcessing() {
        const status = this.getPaymentStatus();
        return status
            ? ["waiting", "waitingCancel", "waitingCard", "waitingScan", "waitingCapture"].includes(
                  status
              )
            : false;
    }

    isForceDoneAllowed() {
        return true;
    }

    isElectronic() {
        return Boolean(this.getPaymentStatus());
    }

    getRefundedOrder() {
        if (this.amount > 0) {
            return null;
        }
        return this.pos_order_id.refunded_order_id ?? null;
    }

    getRefundedPayment() {
        const refundedOrder = this.getRefundedOrder();
        if (!refundedOrder) {
            return null;
        }
        const eligiblePayments = refundedOrder.payment_ids.filter(
            (payment) =>
                payment.payment_provider === this.payment_provider &&
                payment.amount <= Math.abs(this.amount)
        );
        const sortedPayments = sortBy(eligiblePayments, "amount", "desc");
        return sortedPayments.length ? sortedPayments[0] : null;
    }

    _getPaymentCallback() {
        const { promise, resolve, reject } = Promise.withResolvers();
        const callback = (response) => {
            if (response.status === "paid") {
                this.transaction_id = response.final_transaction_id ?? this.transaction_id;
                this.card_no = response.card_no ?? this.card_no;
                this.card_brand = response.card_brand ?? this.card_brand;
                this.card_type = response.card_type ?? this.card_type;
                this.cardholder_name = response.cardholder_name ?? this.cardholder_name;
                this.payment_method_metadata = response.metadata ?? this.payment_method_metadata;
                if (response.final_amount) {
                    this.setAmount(response.final_amount);
                }
                this.handlePaymentResponse(true);
                resolve(response);
            } else if (response.status === "failed") {
                this.handlePaymentResponse(false);
                if (response.error) {
                    reject(new Error(response.error));
                } else {
                    resolve(false);
                }
            }
        };

        return { callback, promise };
    }

    async _startElectronicPayment(completionCallback) {
        const tippingEnabled = Boolean(
            this.config.iface_tipproduct &&
                this.config.tip_product_id &&
                !this.config.set_tip_after_payment
        );
        const extraArgs = {
            partner_id: this.pos_order_id.partner_id?.id,
            order_number: this.pos_order_id.tracking_number,
            allow_tips: tippingEnabled && !this.config.set_tip_after_payment,
            allow_adjustments:
                (tippingEnabled && this.config.set_tip_after_payment) ||
                this.config.module_pos_restaurant,
        };
        if (this.amount < 0) {
            const paymentToRefund = this.getRefundedPayment();
            if (paymentToRefund && this.payment_interface.supportsReversals()) {
                extraArgs.original_payment_timestamp = paymentToRefund.create_date.toUTC().toISO();
                return await this.payment_interface.startReversal(
                    Math.abs(this.amount),
                    this.currency.id,
                    paymentToRefund.transaction_id,
                    extraArgs,
                    completionCallback
                );
            } else {
                return await this.payment_interface.startRefund(
                    Math.abs(this.amount),
                    this.currency.id,
                    extraArgs,
                    completionCallback
                );
            }
        } else {
            return await this.payment_interface.startPayment(
                this.amount,
                this.currency.id,
                extraArgs,
                completionCallback
            );
        }
    }

    // ----- Payment Request -----
    async pay() {
        this.setPaymentStatus("waiting");

        try {
            const { callback, promise } = this._getPaymentCallback();
            const response = await this._startElectronicPayment(callback);
            this.transaction_id = response.transaction_id;

            if (response.status === "pending") {
                if (this.useQr) {
                    this.setPaymentStatus("waitingScan");
                } else if (this.useTerminal || this.useCashMachine) {
                    this.setPaymentStatus("waitingCard");
                }
            }

            if (response.qr_code) {
                this.qr_code = generateQRCodeDataUrl(response.qr_code, { useThemeQr: true });
                return true;
            }

            return promise;
        } catch (error) {
            this.handlePaymentResponse(false);
            throw error;
        }
    }

    async resumePayment() {
        const { callback, promise } = this._getPaymentCallback();
        this.payment_interface.startListening(this.transaction_id, callback);
        return promise;
    }

    async capturePayment() {
        const { callback, promise } = this._getPaymentCallback();
        await this.payment_interface.capturePayment(
            this.amount,
            this.currency.id,
            this.transaction_id,
            { metadata: this.payment_method_metadata },
            callback
        );
        return promise;
    }

    handlePaymentResponse(isPaymentSuccessful) {
        const status = isPaymentSuccessful ? "done" : "retry";
        this.setPaymentStatus(status);
        return isPaymentSuccessful;
    }

    // ----- Payment Cancel -----
    async cancelPayment() {
        this.setPaymentStatus("waitingCancel");
        try {
            const result = await this.payment_interface.cancelTransaction(this.transaction_id);
            if (result.error) {
                throw new Error(result.error);
            }
            return this.handlePaymentCancelResponse(result.success ?? true);
        } catch (error) {
            this.handlePaymentCancelResponse(false);
            throw error;
        }
    }

    handlePaymentCancelResponse(isCancelSuccessful) {
        if (isCancelSuccessful) {
            return true;
        }
        if (this.useTerminal || this.useCashMachine) {
            this.setPaymentStatus("waitingCard");
        } else if (this.useQr) {
            this.setPaymentStatus("waitingScan");
        } else {
            this.setPaymentStatus("waiting");
        }

        return false;
    }

    // ----- Payment Force State -----
    forceDone() {
        this.payment_interface?.stopListening(this.transaction_id);
        this.setPaymentStatus("done");
    }

    forceCancel() {
        this.payment_interface?.stopListening(this.transaction_id);
        this.setPaymentStatus("retry");
    }

    canBeAdjusted() {
        if (this.payment_interface) {
            return Boolean(this.payment_method_metadata?.can_be_adjusted);
        }
        return this.payment_method_id.type !== "cash";
    }

    requiresCapture() {
        if (this.payment_interface) {
            return this.canBeAdjusted() || Boolean(this.payment_method_metadata?.requires_capture);
        }
        return false;
    }

    async adjustAmount(amount) {
        if (!this.payment_interface) {
            return;
        }

        const { promise, callback } = this._getPaymentCallback();
        await this.payment_interface.adjustPayment(
            this.amount + amount,
            this.currency.id,
            this.transaction_id,
            { metadata: this.payment_method_metadata },
            callback
        );

        return promise.then((result) => {
            if (result.status === "paid") {
                this.setAmount(this.amount + amount);
            }
            return result;
        });
    }
}

registry.category("pos_available_models").add(PosPayment.pythonModel, PosPayment);
