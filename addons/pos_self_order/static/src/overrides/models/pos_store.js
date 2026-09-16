import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this._selfOrderNotifications = new Map();
        this.data.connectWebSocket("NEW_SELF_ORDER", async (data) => {
            try {
                await this.data.loadServerOrders([["id", "in", data.order_ids]]);
            } catch {
                this.notification.add(_t("New order could not be loaded from the server."), {
                    type: "warning",
                });
                return;
            }
            for (const orderId of data.order_ids) {
                this._handleSelfOrder(orderId);
            }
        });
        this.data.connectWebSocket("SELF_ORDER_REVIEWED", (data) => {
            for (const orderId of data.order_ids) {
                this._closeSelfOrderNotification(orderId);
            }
        });
    },
    _getOrderNotificationMessage(order) {
        const table = order.self_ordering_table_id;
        if (table?.floor_id) {
            return _t(
                "New order received from %s - Table %s",
                table.floor_id.name,
                table.table_number
            );
        }
        if (order.preset_id?.name) {
            return _t("New %s order received: %s", order.preset_id.name, order.tracking_number);
        }
        return _t("New self order received: %s", order.tracking_number);
    },
    _handleSelfOrder(orderId) {
        const order = this.models["pos.order"].get(orderId);
        if (!order || this._selfOrderNotifications.has(orderId)) {
            return;
        }
        if (!this._selfOrderNotifications.size) {
            this.sound.play("order-receive-tone", {
                loop: true,
                volume: 1,
            });
        }
        const closeNotification = this.notification.add(this._getOrderNotificationMessage(order), {
            type: "success",
            sticky: true,
            buttons: [
                {
                    name: _t("Review Order"),
                    onClick: () => {
                        this.setOrder(order);
                        const stateOverride = {
                            search: {
                                fieldName: "REFERENCE",
                                searchTerm: order.getName(),
                            },
                        };
                        stateOverride.filter = ["paid", "done"].includes(order.state)
                            ? "SYNCED"
                            : "ACTIVE_ORDERS";
                        if (order.preset_id) {
                            stateOverride.selectedPreset = order.preset_id;
                        }
                        this.navigate("TicketScreen", { stateOverride });
                        closeNotification();
                        this._notifySelfOrderReviewed(orderId);
                    },
                },
            ],
            onClose: () => {
                this._selfOrderNotifications.delete(orderId);
                if (!this._selfOrderNotifications.size) {
                    this.sound.stop("order-receive-tone");
                }
            },
        });
        this._selfOrderNotifications.set(orderId, closeNotification);
    },
    _closeSelfOrderNotification(orderId) {
        this._selfOrderNotifications.get(orderId)?.();
    },
    async _notifySelfOrderReviewed(orderId) {
        try {
            await this.data.call("pos.order", "notify_self_order_reviewed", [[orderId]]);
        } catch (error) {
            console.log(error);
        }
    },
    getServerOrdersDomain() {
        const base = super.getServerOrdersDomain();
        if (this.session._self_ordering) {
            return Domain.or([
                base,
                new Domain([
                    ["company_id", "=", this.config.company_id.id],
                    ["state", "=", "draft"],
                    ["source", "=", "kiosk"],
                ]),
            ]);
        }
        return base;
    },
    async redirectToQrForm() {
        const user_data = await this.data.call("pos.config", "get_pos_qr_order_data", [
            this.config.id,
        ]);
        return await this.action.doAction({
            type: "ir.actions.client",
            tag: "pos_qr_stands",
            params: { data: user_data },
        });
    },
});
