import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { onWillStart } from "@odoo/owl";
import { useSquareApp } from "../../hooks/use_square_app";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.squareApp = useSquareApp();
        onWillStart(async () => {
            await this.squareApp.process();
        });
    },

    async addNewPaymentLine(pm, args = {}) {
        if (pm.usesSquareApp()) {
            // The Square app has to be opened by the gesture that adds the line.
            await this.squareApp.start(pm);
            return;
        }
        return await super.addNewPaymentLine(...arguments);
    },
});
