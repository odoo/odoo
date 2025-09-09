import { patch } from "@web/core/utils/patch";
import { SelfOrder } from "@pos_self_order/app/services/self_order_service";
import { session } from "@web/session";

patch(SelfOrder.prototype, {
    async setup(...args) {
        await super.setup(...args);
        this.onlinePaymentStatus = null;
        this.data.connectWebSocket("ONLINE_PAYMENT_STATUS", ({ status, data }) => {
<<<<<<< fe4c097c342b84b2fd1ba7e93094b4f2427d4e3b:addons/pos_online_payment_self_order/static/src/app/services/self_order_service.js
            if (
                data["pos.order"].length === 0 ||
                data["pos.order"][0].uuid !== this.currentOrder.uuid
            ) {
                return;
            }
||||||| 178dff30131a93680dfd994fd22b29a766ee9354:addons/pos_online_payment_self_order/static/src/self_order_service.js
=======
            // Ignore updates for orders from other devices
            let order = this.models["pos.order"].find((o) => o.uuid === data["pos.order"][0].uuid);
            if (!order) {
                return;
            }
>>>>>>> 8f1077c211feeb9ee8676f395ab4ae2a25f91fe3:addons/pos_online_payment_self_order/static/src/self_order_service.js
            this.models.loadData(data, [], false);
            this.onlinePaymentStatus = status;
            this.paymentError = status === "fail";

            order = this.models["pos.order"].find(
                (o) => o.access_token === data["pos.order"][0].access_token
            );
            if (
                status === "success" &&
                !this.currentOrder.access_token &&
                order &&
                order.uuid === this.currentOrder.uuid
            ) {
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
        const pmIds = this.config.payment_method_ids.map((o) => o.id);
        const online_pms = pms.filter(
            (rec) =>
                rec.is_online_payment &&
                (this.config.self_order_online_payment_method_id?.id === rec.id ||
                    (this.config.self_ordering_mode === "kiosk" && pmIds.includes(rec.id)))
        );
        return [...new Set([...pm, ...online_pms])];
    },
});
