/** @odoo-module */

import PaymentScreen from "@point_of_sale/js/Screens/PaymentScreen/PaymentScreen";
import Registries from "@point_of_sale/js/Registries";
import session from "web.session";

const L10nCoPosPaymentScreen = (PaymentScreen) =>
    class extends PaymentScreen {
        async _postPushOrderResolve(order, order_server_ids) {
            try {
                if (this.env.pos.is_colombian_country()) {
                    const result = await this.rpc({
                        model: "pos.order",
                        method: "search_read",
                        domain: [["id", "in", order_server_ids]],
                        fields: ["name"],
                        context: session.user_context,
                    });
                    order.set_l10n_co_dian(result[0].name || false);
                }
            } catch {
                // FIXME this doesn't seem correct but is equivalent to return in finally which we had before.
            }
            return super._postPushOrderResolve(...arguments);
        }
    };

Registries.Component.extend(PaymentScreen, L10nCoPosPaymentScreen);

export default PaymentScreen;
