/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, "l10n_co_pos.PaymentScreen", {
    async _postPushOrderResolve(order, order_server_ids) {
        const _super = this._super;
        try {
            if (this.pos.is_colombian_country()) {
                const result = await this.orm.searchRead(
                    "pos.order",
                    [["id", "in", order_server_ids]],
                    ["name"]
                );
                order.set_l10n_co_dian(result[0].name || false);
            }
        } catch {
            // FIXME this doesn't seem correct but is equivalent to return in finally which we had before.
        }
        return _super(...arguments);
    },
});
