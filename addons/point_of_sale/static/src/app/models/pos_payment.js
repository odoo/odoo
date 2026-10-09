import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
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

    get useQr() {
        return this.payment_method_id.useQr;
    }

    get useBankQrCode() {
        return this.payment_method_id.useBankQrCode;
    }

    get displayName() {
        return this.payment_method_id.name;
    }

    isSelected() {
        return this.pos_order_id?.uiState?.selected_paymentline_uuid === this.uuid;
    }

    setAmount(value, currency = this.pos_order_id.currency) {
        this.pos_order_id.assertEditable();

        if (currency != this.pos_order_id.currency) {
            this.amount_currency = parseFloat(value) || 0;
            this.amount = this.pos_order_id.currency.round(
                this.currency.convertToDefaultCurrency(this.amount_currency)
            );
        } else {
            this.amount = this.pos_order_id.currency.round(parseFloat(value) || 0);
            this.amount_currency = this.currency.convert(this.amount);
        }
    }

    getAmount() {
        return this.amount || 0;
    }

    get isSettled() {
        return !this.payment_status || this.payment_status === "done";
    }

    get isProcessing() {
        return [
            "waiting",
            "waiting_cancel",
            "waiting_card",
            "waiting_scan",
            "waiting_capture",
            "force_done",
        ].includes(this.payment_status);
    }

    get isAmountEditable() {
        return !this.payment_interface || ["pending", "retry"].includes(this.payment_status);
    }

    get isRefund() {
        return this.amount < 0;
    }

    // ----- Payment Request -----
    async pay() {
        this.payment_status = "waiting";
        try {
            const success = await this.payment_interface.sendPaymentRequest(this);
            return this.handlePaymentResponse(success);
        } catch (error) {
            this.handlePaymentResponse(false);
            throw error;
        }
    }

    handlePaymentResponse(isPaymentSuccessful) {
        this.payment_status = isPaymentSuccessful ? "done" : "retry";
        return isPaymentSuccessful;
    }

    // ----- Payment Cancel -----
    async cancelPayment() {
        this.payment_status = "waiting_cancel";
        try {
            const success = await this.payment_interface.sendPaymentCancel(this);
            return this.handlePaymentCancelResponse(success);
        } catch (error) {
            this.handlePaymentCancelResponse(false);
            throw error;
        }
    }

    handlePaymentCancelResponse(isCancelSuccessful) {
        if (isCancelSuccessful) {
            this.payment_status = "retry";
        } else if (this.useTerminal) {
            this.payment_status = "waiting_card";
        } else if (this.useQr) {
            this.payment_status = "waiting_scan";
        } else {
            this.payment_status = "waiting";
        }

        return isCancelSuccessful;
    }

    // ----- Payment Force State -----
    forceDone() {
        this.payment_status = "done";
    }

    forceCancel() {
        this.payment_status = "retry";
    }

    /**
     * @param {object} - refundedPaymentLine
     * Override in dependent modules to update the refund payment line with the refunded payment line
     */
    updateRefundPaymentLine(refundedPaymentLine) {}

    canBeAdjusted() {
        if (this.payment_interface) {
            return this.payment_interface.canBeAdjusted(this.uuid);
        }
        return this.payment_method_id.type !== "cash" && !this.useBankQrCode;
    }

    async adjustAmount(amount) {
        if (this.payment_interface) {
            this.amount += amount;
            await this.payment_interface.sendPaymentAdjust(this.uuid);
        }
    }
}

registry.category("pos_available_models").add(PosPayment.pythonModel, PosPayment);
