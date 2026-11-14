/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    async _postPushOrderResolve(order, _order_server_ids) {
        if (this.pos.company.l10n_es_edi_verifactu_required) {
            order.invoice_name = await this.pos.data.call(
                "pos.order",
                "l10n_es_edi_verifactu_get_invoice_name",
                [order.id]
            );
        }
        return super._postPushOrderResolve(...arguments);
    },
});
