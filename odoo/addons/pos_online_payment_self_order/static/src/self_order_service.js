/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { SelfOrder } from "@pos_self_order/app/self_order_service";
import { session } from "@web/session";

patch(SelfOrder.prototype, {
    async setup(...args) {
        await super.setup(...args);
        this.onlinePaymentStatus = null;
    },
    finalizeOrder() {
        const order = this.currentOrder;

        this.updateOrdersFromServer([order], [order.access_token]);
        this.router.navigate("confirmation", {
            orderAccessToken: order.access_token,
            screenMode: "order",
        });
    },
    getOnlinePaymentUrl(
        { id: order_id, access_token: order_access_token, pos_config_id: order_pos_config_id },
        exitRoute = true
    ) {
        const baseUrl = session.base_url;
        const order = this.currentOrder;
        let exitRouteUrl = baseUrl;

        if (exitRoute) {
            exitRouteUrl += `/pos-self/${order_pos_config_id}`;

            if (this.config.self_ordering_pay_after === "each") {
                exitRouteUrl += `/confirmation/${order.access_token}/order`;
            }

            exitRouteUrl += `?access_token=${this.access_token}`;
        }

        const exit = encodeURIComponent(exitRouteUrl);
        return `${baseUrl}/pos/pay/${order_id}?access_token=${order_access_token}&exit_route=${exit}`;
    },
});
