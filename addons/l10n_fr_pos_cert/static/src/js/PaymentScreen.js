/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/js/Screens/PaymentScreen/PaymentScreen";
import { patch } from "@web/core/utils/patch";
import session from "web.session";

patch(PaymentScreen.prototype, "l10n_fr_pos_cert.PaymentScreen", {
    async _postPushOrderResolve(order, order_server_ids) {
        const _super = this._super;
        try {
            if (this.env.pos.is_french_country()) {
                const result = await this.rpc({
                    model: "pos.order",
                    method: "search_read",
                    domain: [["id", "in", order_server_ids]],
                    fields: ["l10n_fr_hash"],
                    context: session.user_context,
                });
                order.set_l10n_fr_hash(result[0].l10n_fr_hash || false);
            }
        } catch {
            // FIXME this doesn't seem correct but is equivalent to return in finally which we had before.
        }
        return _super(...arguments);
    },
});
