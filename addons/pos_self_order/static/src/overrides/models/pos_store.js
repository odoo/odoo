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
                await this.getServerOrders();
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
        const message = _t("New Self Order: %s", order.getName());
        const closeNotification = this.notification.add(message, {
            type: "success",
            sticky: true,
            buttons: [
                {
                    name: _t("Load"),
                    onClick: () => {
                        this.setOrder(order);
                        this.navigateToOrderScreen(order);
                        closeNotification();
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
