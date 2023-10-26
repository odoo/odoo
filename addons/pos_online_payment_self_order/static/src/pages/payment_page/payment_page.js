/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";
import { _t } from "@web/core/l10n/translation";

patch(PaymentPage.prototype, {
    async startPayment() {
        let order = this.selfOrder.currentOrder;
        const pm = this.selectedPaymentMethod;
        const device = this.selfOrder.config.self_ordering_mode;

        if (!pm || !pm.is_online_payment) {
            return super.startPayment(...arguments);
        } else {
            order = await this.selfOrder.sendDraftOrderToServer();
        }

        if (device === "kiosk") {
            const url = this.selfOrder.getOnlinePaymentUrl(order, false);
            this.generateQrcodeImg(url);
        } else {
            this.checkAndOpenPaymentPage(order);
        }
    },
    get selectedPaymentIsOnline() {
        const paymentMethods = this.selectedPaymentMethod;
        return (
            paymentMethods &&
            paymentMethods.is_online_payment
        );
    },
    generateQrcodeImg(url) {
        const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
        const qr_code_svg = new XMLSerializer().serializeToString(codeWriter.write(url, 150, 150));
        this.state.qrImage = "data:image/svg+xml;base64," + window.btoa(qr_code_svg);
    },
    async checkAndOpenPaymentPage(order) {
        if (order.state === "draft") {
            const onlinePaymentUrl = this.selfOrder.getOnlinePaymentUrl(order, true);
            window.open(onlinePaymentUrl, "_self");
        } else {
            this.selfOrder.notification.add(
                _t("The current order cannot be paid (maybe it is already paid)."),
                { type: "danger" }
            );
        }
    },
});
