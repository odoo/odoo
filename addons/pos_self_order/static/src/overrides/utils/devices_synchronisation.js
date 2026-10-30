import DevicesSynchronisation from "@point_of_sale/app/utils/devices_synchronisation";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(DevicesSynchronisation.prototype, {
    setup() {
        super.setup(...arguments);
        this.notifiedLines = new Set();
    },

    async processDynamicRecords(dynamicRecords) {
        const processed = await super.processDynamicRecords(dynamicRecords);
        if (!processed["pos.order"]?.length) {
            return processed;
        }
        const ordersToNotify = processed["pos.order"].filter((o) =>
            ["mobile", "kiosk"].includes(o.source)
        );

        const isPayAfterEachWithOnlinePayment =
            this.pos.config.self_order_online_payment_method_id &&
            this.pos.config.self_ordering_pay_after === "each";

        for (const order of ordersToNotify) {
            if (order.state === "cancel") {
                this.snoozeNotification(order.id);
                continue;
            }
            const orderPaid = ["paid", "done"].includes(order.state);
            if (isPayAfterEachWithOnlinePayment && !orderPaid) {
                continue;
            }
            const lineKeys = order.lines.map((line) => `${line.uuid}:${line.qty}`);
            if (lineKeys.every((key) => this.notifiedLines.has(key))) {
                continue;
            }
            lineKeys.forEach((key) => this.notifiedLines.add(key));
            this.displayNotification(order, {
                message: order.getSelfOrderNotificationMessage(),
                name: _t("Review Orders"),
                onClick: () => {
                    const isPaid = ["paid", "done"].includes(order.state);
                    const stateOverride = {
                        selectedPreset: order.preset_id || false,
                        filter: isPaid ? "SYNCED" : "ACTIVE_ORDERS",
                        search: {
                            fieldName: "REFERENCE",
                            searchTerm: order.getName(),
                        },
                    };

                    this.pos.setOrder(order);
                    this.pos.navigate("TicketScreen", { stateOverride });
                    this.snoozeNotification(order.id, true);
                },
            });
        }
        return processed;
    },
});
