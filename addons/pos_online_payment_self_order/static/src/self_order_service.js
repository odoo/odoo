/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { SelfOrder } from "@pos_self_order/self_order_service";
import { session } from "@web/session";

patch(SelfOrder.prototype, "pos_online_payment_self_order.SelfOrder", {
    openOnlinePaymentPage({ id: order_id, access_token: order_access_token, pos_config_id: order_pos_config_id }) {
        const baseUrl = session.base_url;
        let exitRouteUrl = baseUrl + "/menu/" + order_pos_config_id + "?access_token=" + this.access_token;
        const tableIdentifier = this.table?.identifier;
        if (tableIdentifier) {
            exitRouteUrl += "&table_identifier=" + tableIdentifier;
        }
        const exitRoute = encodeURIComponent(exitRouteUrl);
        window.open(baseUrl + `/pos/pay/${order_id}?access_token=${order_access_token}&exit_route=${exitRoute}`, "_self");
    },
});
