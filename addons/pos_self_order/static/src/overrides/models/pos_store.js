import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket(
            "SELF_ORDER_PRINT_REQ",
            async ({ order_id }) => await this._handleSelfOrderPrintReq(order_id)
        );
    },
    async _handleSelfOrderPrintReq(orderId) {
        try {
            await this.getServerOrders();
        } catch {
            this.notification.add(
                _t(
                    "Could not fetch the latest self-order from the server. Please check your connection."
                ),
                {
                    type: "danger",
                    title: _t("Connection Error"),
                }
            );
        }

        const order = this.models["pos.order"].get(orderId);

        if (order && order.state === "draft") {
            if (
                !order.last_order_preparation_change ||
                !order.last_order_preparation_change.lines
            ) {
                order.last_order_preparation_change = {
                    lines: {},
                    general_customer_note: "",
                    internal_note: "",
                    sittingMode: 0,
                    metadata: {},
                };
            }

            await this.sendOrderInPreparation(order);
        }
    },
    async getServerOrders() {
        if (this.session._self_ordering) {
            await this.data.loadServerOrders([
                ["company_id", "=", this.config.company_id.id],
                ["state", "=", "draft"],
                ["source", "=", "kiosk"],
            ]);
        }

        return await super.getServerOrders(...arguments);
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
