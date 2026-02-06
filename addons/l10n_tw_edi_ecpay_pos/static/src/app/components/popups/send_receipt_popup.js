import { Component, xml } from "@odoo/owl";
import { EcpayCertificateReceipt } from "@l10n_tw_edi_ecpay_pos/app/components/order_receipt/ecpay_certificate_receipt";
import { EcpayTransactionReceipt } from "@l10n_tw_edi_ecpay_pos/app/components/order_receipt/ecpay_transaction_receipt";
import { OrderReceipt } from "@point_of_sale/app/components/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";
import { SendReceiptPopup } from "@point_of_sale/app/components/popups/send_receipt_popup/send_receipt_popup";

class EcpaySendReceiptImage extends Component {
    static components = {
        OrderReceipt,
        EcpayCertificateReceipt,
        EcpayTransactionReceipt,
    };
    static props = {
        order: Object,
        basic_receipt: { type: Boolean, optional: true },
        includeEcpay: { type: Boolean, optional: true },
    };
    static template = xml`
        <div>
            <OrderReceipt order="props.order" basic_receipt="props.basic_receipt"/>
            <t t-if="props.includeEcpay">
                <EcpayCertificateReceipt order="props.order"/>
                <EcpayTransactionReceipt order="props.order"/>
            </t>
        </div>
    `;
}

patch(SendReceiptPopup.prototype, {
    async generateTicketImage(basicReceipt = false) {
        const order = this.order;
        const isOffline = this.pos.data.network.offline;
        let includeEcpay =
            !basicReceipt && !isOffline && order?.isPrintEcpayInvoice && !order.ecpay_error;

        if (includeEcpay) {
            await this.pos._getUniformInvoiceData(order, { throw: true });
            includeEcpay = !order.ecpay_error;
        }

        return await this.renderer.toJpeg(
            EcpaySendReceiptImage,
            {
                order,
                basic_receipt: basicReceipt,
                includeEcpay,
            },
            { addClass: "pos-receipt-print p-3" }
        );
    },
});
