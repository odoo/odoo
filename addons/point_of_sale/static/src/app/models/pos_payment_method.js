import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { _t } from "@web/core/l10n/translation";

export class PosPaymentMethod extends Base {
    static pythonModel = "pos.payment.method";

    get useTerminal() {
        return this.payment_method_type === "terminal";
    }

    get useQrPayment() {
        return this.payment_method_type === "qr_payment";
    }

    get useBankTransfer() {
        return this.payment_method_type === "bank_transfer";
    }

    get usePaymentInterface() {
        return Boolean(this.payment_interface);
    }

    isAvailable(order) {
        return (
            !order.isRefund || !this.payment_interface || this.payment_interface.supports_refunds
        );
    }

    get paymentInterfaceKey() {
        return this.useBankTransfer ? this.payment_method_type : this.payment_provider;
    }

    get config() {
        return this.models["pos.config"].get(odoo.pos_config_id);
    }

    get availableCurrencies() {
        if (["bank", "cash"].includes(this.type)) {
            // Always include the company currency first, then add the other currencies of the payment method
            return [
                this.config.currency_id,
                ...this.currency_ids.filter((c) => c.id !== this.config.currency_id.id),
            ];
        }

        return [this.config.currency_id];
    }

    /**
     * Check if the processing `line` prevents this method from starting a
     * payment on `order`. Override it for the lines a provider handles and
     * call super for the others.
     */
    isBlockedBy(line, { order, paymentline }) {
        const type = this.payment_method_type;
        return type !== "none" && line.payment_method_id.payment_method_type === type;
    }

    /**
     * Message shown when `line` blocks this method.
     */
    getBlockingMessage(line) {
        return _t("There is already an electronic payment in progress.");
    }

    /**
     * Check if this method can add or send a payment on `order` right now.
     * `paymentline` is the line being sent, if any.
     */
    canStartPayment({ order, paymentline } = {}) {
        if (!this.usePaymentInterface) {
            return { status: true, message: "" };
        }
        const blockingLine = this.models["pos.payment"].find(
            (line) =>
                line.isProcessing &&
                line.uuid !== paymentline?.uuid &&
                !line.pos_order_id?.finalized &&
                this.isBlockedBy(line, { order, paymentline })
        );
        return blockingLine
            ? { status: false, message: this.getBlockingMessage(blockingLine) }
            : { status: true, message: "" };
    }
}

registry.category("pos_available_models").add(PosPaymentMethod.pythonModel, PosPaymentMethod);
