import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { serializeDateTime } from "@web/core/l10n/dates";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { generateQRCodeDataUrl } from "@point_of_sale/utils";
import { QRPopup } from "@point_of_sale/app/components/popups/qr_code_popup/qr_code_popup";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";

export class PaymentOnline extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.supports_refunds = false;
        this.pendingRequests = {};
    }

    async sendPaymentRequest(line) {
        const order = line.pos_order_id;
        if (!this.pos.currency.isPositive(line.amount)) {
            this.showError(
                _t("Invalid online payment"),
                _t(
                    "Online payments cannot have a negative amount (%s: %s).",
                    line.payment_method_id.name,
                    this.pos.formatCurrency(line.amount)
                )
            );
            return false;
        }
        if (order.paymentsRequireCustomer([line]) && !order.partner_id?.email) {
            this.showError(
                _t("Payment provider requirement"),
                _t("Please ensure you have a customer with an email address on this order.")
            );
            return false;
        }

        order.date_order = serializeDateTime(luxon.DateTime.now());
        // The server writes the payment on the line, so it must exist there first
        await this.pos.syncAllOrders({ orders: [order] });
        if (!line.isSynced) {
            this.showError(
                _t("Online payment unavailable"),
                _t("The QR code payment could not be generated.")
            );
            return false;
        }
        if (line.payment_status === "done") {
            return true;
        }

        const opData = await this.pos.updateOnlinePaymentsDataWithServer(order, line.amount);
        if (!opData) {
            this.showError(
                _t("Online payment unavailable"),
                _t(
                    "There is a problem with the server. The order online payment status cannot be retrieved."
                ),
                { showReloadButton: true }
            );
            return false;
        }
        if (opData.isPaid) {
            return line.payment_status === "done";
        }
        if (opData.modified_payment_lines) {
            if (line.payment_status === "done") {
                return true;
            }
            this.showError(
                _t("Updated online payments"),
                _t("There are online payments that were missing in your view.")
            );
            return false;
        }
        if (this.pos.currency.isPositive(line.amount - opData.amount_unpaid)) {
            this.showError(
                _t("Invalid online payment"),
                _t(
                    "The online payment amount (%s) is higher than the remaining unpaid amount of the order (%s).",
                    this.pos.formatCurrency(line.amount),
                    this.pos.formatCurrency(opData.amount_unpaid)
                )
            );
            return false;
        }

        const isPaid = await this.showQrCode(line);
        if (!isPaid) {
            // A late scan of the QR code then asks for the whole amount due
            this.pos.updateOnlinePaymentsDataWithServer(order, 0);
        }
        return isPaid;
    }

    async sendPaymentCancel(line) {
        this.pendingRequests[line.uuid]?.(false);
        return true;
    }

    checkPaymentStatus(line) {
        if (line.payment_status === "done") {
            this.pendingRequests[line.uuid]?.(true);
        }
    }

    showQrCode(line) {
        const order = line.pos_order_id;
        const qrCodeUrl = `${this.pos.config._base_url}/pos/pay/${order.id}?access_token=${order.access_token}`;
        const onlinePaymentData = {
            amount: this.pos.formatCurrency(line.amount),
            qrCode: generateQRCodeDataUrl(qrCodeUrl),
        };
        order.onlinePaymentData = onlinePaymentData;
        return new Promise((resolve) => {
            const closeQrCode = this.dialog.add(QRPopup, onlinePaymentData, {
                onClose: () => this.pendingRequests[line.uuid]?.(false),
            });
            this.pendingRequests[line.uuid] = (isPaid) => {
                delete this.pendingRequests[line.uuid];
                order.onlinePaymentData = {};
                closeQrCode();
                resolve(isPaid);
            };
        });
    }

    showError(title, body, options = {}) {
        this.dialog.add(AlertDialog, { title, body, ...options });
    }
}

registry.category("pos_payment_providers").add("online", PaymentOnline);
