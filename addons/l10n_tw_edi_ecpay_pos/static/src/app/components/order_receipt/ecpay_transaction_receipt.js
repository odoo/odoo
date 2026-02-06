import { OrderReceipt } from "@point_of_sale/app/components/receipt/order_receipt";

export class EcpayTransactionReceipt extends OrderReceipt {
    static template = "l10n_tw_edi_ecpay_pos.EcpayTransactionReceipt";

    get orderLines() {
        return this.order.getOrderlines();
    }
}
