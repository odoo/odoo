import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);

        // Usefull when using several devices with table synchronisation
        this.orderUuidAfterMerge = "";

        onWillStart(async () => {
            // Must be done in onWillStart readDataFromServer will make
            // this.currentOrder undefined during an animation frame,
            // so we must read data from the server beforehand.
            try {
                const firstLine = this.currentOrder.lines[0];
                const uuidBefore = this.currentOrder?.uuid;
                await this.pos.deviceSync.readDataFromServer();
                const uuidAfter = firstLine?.order_id?.uuid;

                // If an order is merged its uuid will change, so we need
                // to detect it and give it to get currentOrder correctly.
                if (uuidBefore && uuidAfter && uuidAfter !== uuidBefore) {
                    this.orderUuidAfterMerge = uuidAfter;
                    this.pos.notification.add(
                        _t("Someone else just updated the order; please check it before paying."),
                        {
                            type: "warning",
                        }
                    );
                }
            } catch {
                this.pos.notification.add(
                    _t(
                        "Failed to read data from the server. If the order was updated by someone else, you might not have the latest changes."
                    ),
                    {
                        type: "danger",
                    }
                );
            }
        });
    },

    get currentOrder() {
        const order = super.currentOrder;
        if (!order) {
            return this.pos.models["pos.order"].getBy("uuid", this.orderUuidAfterMerge);
        }
        return order;
    },
});
