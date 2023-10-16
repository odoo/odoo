/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";

patch(PaymentPage.prototype, {
    async startPayment() {
        let order = this.selfOrder.currentOrder;
        const selfMode = this.selfOrder.config.self_ordering_mode;
        const pm = this.selectedPaymentMethod;

        if (selfMode !== "kiosk" || !pm || !pm.is_online_payment) {
            return super.startPayment(...arguments);
        } else {
            order = await this.selfOrder.sendDraftOrderToServer();
        }

        const url = this.selfOrder.getOnlinePaymentUrl(order, false);
        this.generateQrcodeImg(url);
    },
    get selectedPaymentIsOnline() {
        const paymentMethods = this.selectedPaymentMethod;
        return (
            paymentMethods &&
            paymentMethods.is_online_payment &&
            this.selfOrder.config.self_ordering_mode === "kiosk"
        );
    },
    generateQrcodeImg(url) {
        const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
        const qr_code_svg = new XMLSerializer().serializeToString(codeWriter.write(url, 150, 150));
        this.state.qrImage = "data:image/svg+xml;base64," + window.btoa(qr_code_svg);
    },
});
