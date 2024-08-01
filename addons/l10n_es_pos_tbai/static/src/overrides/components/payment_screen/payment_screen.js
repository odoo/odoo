/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { qrCodeSrc } from "@point_of_sale/utils";

patch(PaymentScreen.prototype, {
    async _postPushOrderResolve(order, order_server_ids) {
        if (this.pos.config.l10n_es_tbai_is_required) {
            const l10n_es_pos_tbai_qrurl = await this.pos.data.call(
                "pos.order",
                "get_l10n_es_pos_tbai_qrurl",
                [order.id]
            );
            order.l10n_es_pos_tbai_qrsrc = l10n_es_pos_tbai_qrurl
                ? qrCodeSrc(l10n_es_pos_tbai_qrurl)
                : undefined;
        }
        return super._postPushOrderResolve(...arguments);
    },
});
