import { patch } from "@web/core/utils/patch";
import { BillScreen } from "@pos_restaurant/app/bill_screen/bill_screen";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { onWillStart } from "@odoo/owl";
import { MODEL, POS_ORDER_QR_TYPE, PAYMENT_METHODS_MAPPING } from "./const";

patch(BillScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");

        onWillStart(async () => {
            await this._generateQrCode();
        });
    },

    async _generateQrCode() {
        /** 
         * Generate Payway QR code for the printed bill in POS resturant.
         */

        const order = this.pos.get_order();
        try {

            if (order.state !== "draft") {
                // Not new order
                order.payway_qr_image = "";
                return;
            }

            const payment = order.payment_ids.at(-1);
            if (!payment) {
                order.payway_qr_image = "";
                return;
            }

            if (
                !payment.payment_method_id ||
                payment.payment_method_id.payment_method_type != "qr_code" ||
                payment.payment_method_id.qr_code_method != PAYMENT_METHODS_MAPPING["abapay_khqr"] ||
                !payment.payment_method_id.allow_qr_on_bill
            ) {
                order.payway_qr_image = "";
                return;
            }

            payment.transaction_id = this.pos._paywayCreateTxnId(payment);
            user.updateContext({
                model: MODEL,
                qr_type: POS_ORDER_QR_TYPE["bill"],
                qr_tran_id: payment.transaction_id,
            });

            const qr = await this.orm.call("pos.payment.method", "get_qr_code", [
                [payment.payment_method_id.id],
                payment.amount,
                payment.pos_order_id.name + " " + payment.pos_order_id.tracking_number,
                "",
                this.pos.currency.id,
                payment.pos_order_id.partner_id?.id,
            ]);

            order.payway_qr_image = qr || "";

        } catch (error) {
            order.payway_qr_image = "";
        }
    }
})