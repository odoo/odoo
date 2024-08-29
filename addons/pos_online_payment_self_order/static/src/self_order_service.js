import { patch } from "@web/core/utils/patch";
import { SelfOrder } from "@pos_self_order/app/self_order_service";
import { session } from "@web/session";

patch(SelfOrder.prototype, {
    async setup(...args) {
        await super.setup(...args);
        this.onlinePaymentStatus = null;
        this.onNotified("ONLINE_PAYMENT_STATUS", ({ status, data }) => {
            this.models.loadData(data, [], false);
            this.onlinePaymentStatus = status;
            this.paymentError = status === "fail";

            const order = this.models["pos.order"].find(
                (o) => o.access_token === data["pos.order"][0].access_token
            );
            if (status === "success" && !this.currentOrder.access_token && order) {
                this.confirmationPage("order", this.config.self_ordering_mode, order.access_token);
            }
        });
    },
    getOnlinePaymentUrl(
        { id: order_id, access_token: order_access_token, config_id: order_pos_config_id },
        exitRoute = true
    ) {
        const baseUrl = session.base_url;
        const order = this.currentOrder;
        let exitRouteUrl = baseUrl;

        if (exitRoute) {
            let table = "";
            exitRouteUrl += `/pos-self/${order_pos_config_id.id}`;

            if (this.config.self_ordering_pay_after === "each") {
                exitRouteUrl += `/confirmation/${order.access_token}/order`;
            }

            if (this.currentTable) {
                table = `&table_identifier=${this.currentTable.identifier}`;
            }

            exitRouteUrl += `?access_token=${this.access_token}${table}`;
        }

        const exit = encodeURIComponent(exitRouteUrl);
        return `${baseUrl}/pos/pay/${order_id}?access_token=${order_access_token}&exit_route=${exit}`;
    },
    filterPaymentMethods(pms) {
        const pm = super.filterPaymentMethods(...arguments);
        const online_pms = pms.filter((rec) => rec.is_online_payment);
        return [...new Set([...pm, ...online_pms])];
    },
});
