import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";

export class EcpayCertificateReceipt extends OrderReceipt {
    static template = "l10n_tw_edi_ecpay_pos.EcpayCertificateReceipt";

    get companyLogo() {
        return this.order.config.receiptCompanyLogoUrl;
    }

    get qrCodeLeft() {
        return this.order.qrcode_left ? this.getEcpayQrcode(this.order.qrcode_left) : undefined;
    }

    get qrCodeRight() {
        return this.order.qrcode_right ? this.getEcpayQrcode(this.order.qrcode_right) : undefined;
    }

    getEcpayQrcode(data) {
        const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
        const qrCodeSvg = new XMLSerializer().serializeToString(codeWriter.write(data, 250, 250));
        return "data:image/svg+xml;base64," + window.btoa(qrCodeSvg);
    }
}
