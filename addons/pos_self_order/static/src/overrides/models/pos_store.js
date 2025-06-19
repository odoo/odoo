import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this._selfOrderData = new Map();

        this.data.connectWebSocket("NEW_SELF_ORDER", (data) => {
            data.order_ids.forEach((order_id) => {
                this._handleSelfOrder(order_id);
            });
        });
    },

    getSelfOrderNotificationOptions(order) {
        return {
            type: "success",
            sticky: true,
            buttons: [
                {
                    name: _t("Load"),
                    onClick: () => {
                        this.setOrder(order);
                        this.navigateToOrderScreen(order);
                        this._selfOrderData.get(order.id)?.closeNotification();
                        this._selfOrderData.delete(order.id);
                    },
                },
            ],
        };
    },

    async _handleSelfOrder(order_id) {
        try {
            await this.getServerOrders();
        } catch {
            return this.notification.add(_t("New order could not be loaded from the server."), {
                type: "warning",
                sticky: false,
            });
        }

        const newOrder = this.models["pos.order"].get(order_id);
        if (
            !newOrder?.table_id?.id ||
            newOrder._notified ||
            (this.config.self_ordering_pay_after === "each" &&
                this.config.self_order_online_payment_method_id?.is_online_payment)
        ) {
            return;
        }

        newOrder._notified = true;
        this.sound.play("order-receive-tone");

        const closeNotification = this.notification.add(
            _t("Self Order: Table %s", newOrder.table_id.table_number),
            this.getSelfOrderNotificationOptions(newOrder)
        );

        this._selfOrderData.set(order_id, { closeNotification });
    },

    async getServerOrders() {
        if (this.session._self_ordering) {
            await this.loadServerOrders([
                ["company_id", "=", this.config.company_id.id],
                ["state", "=", "draft"],
                "|",
                ["pos_reference", "ilike", "Kiosk"],
                ["pos_reference", "ilike", "Self-Order"],
                ["table_id", "=", false],
            ]);
        }

        return await super.getServerOrders(...arguments);
    },
});
