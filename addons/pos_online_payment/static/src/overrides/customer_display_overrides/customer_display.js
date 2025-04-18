import { patch } from "@web/core/utils/patch";
import { OnlinePaymentPopup } from "@pos_online_payment/app/components/popups/online_payment_popup/online_payment_popup";
import { useEffect } from "@odoo/owl";
import { CustomerDisplay } from "@point_of_sale/customer_display/customer_display";
import { useSingleDialog } from "@point_of_sale/customer_display/utils";

patch(CustomerDisplay.prototype, {
    setup() {
        super.setup(...arguments);
        const singleDialog = useSingleDialog();
        useEffect(
            (details) => {
                if (details?.formattedAmount) {
                    singleDialog.open(OnlinePaymentPopup, details);
                } else {
                    singleDialog.close();
                }
            },
            () => [this.order.onlinePaymentData]
        );
    },
});
