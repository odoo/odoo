import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";

import { PAYWAY_QR_CODE_METHOD, MODEL, POS_ORDER_QR_TYPE } from "./const";

patch(PosStore.prototype, {

    async showQR(payment) {

        // Use Odoo receipt number for payway unique transaction id
        payment.transaction_id = this._paywayCreateTxnId(payment);
        user.updateContext({
            model: MODEL,
            qr_type: POS_ORDER_QR_TYPE["screen"],
            qr_tran_id: payment.transaction_id,
        });

        return await super.showQR(payment);
    },

    async printReceipt({
        basic = false,
        order = this.get_order(),
        printBillActionTriggered = false,
    } = {}) {
        const res = await super.printReceipt({ basic, order, printBillActionTriggered });
        const payment = order.payment_ids.at(-1);

        if (
            printBillActionTriggered &&
            payment &&
            PAYWAY_QR_CODE_METHOD.includes(payment.payment_method_id.qr_code_method) &&
            payment.payment_method_id.allow_qr_on_bill
        ) {
            // Count number of printed bill for payway QR
            order.payway_bill_nb_print = (order.payway_bill_nb_print || 0) + 1;
        }
        return res;
    },

    _paywayCreateTxnId(payment) {
        const today = new Date();
        const day = String(today.getDate()).padStart(2, '0');
        const month = String(today.getMonth() + 1).padStart(2, '0');
        const year = String(today.getFullYear()).slice(-2);

        const formattedDate = year + month + day;
        const orderReference = payment.pos_order_id.pos_reference
            .split(" ")
            .at(-1)
            .replaceAll("-", "");

        const transaction_id = `P${formattedDate}${orderReference}`;
        return transaction_id;
    }
});