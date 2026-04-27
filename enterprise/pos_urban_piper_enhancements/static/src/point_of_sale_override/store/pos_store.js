import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    /**
     * @override
     */
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket("FUTURE_ORDER_NOTIFICATION", async (orderIds) => {
            this.sound.play("notification");
            this.notification.add(_t("Scheduled Order"), {
                type: "info",
                sticky: true,
            });
            const futureOrders = this.models["pos.order"].filter((o) => orderIds.includes(o.id));
            for (const order of futureOrders) {
                try {
                    await this.checkPreparationStateAndSentOrderInPreparation(order);
                } catch {
                    this.notification.add(
                        _t("Error to send delivery order in preparation display."),
                        {
                            type: "warning",
                            sticky: false,
                        }
                    );
                }
            }
        });
    },
});
