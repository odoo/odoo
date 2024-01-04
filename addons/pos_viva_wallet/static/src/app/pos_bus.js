/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosBus } from "@point_of_sale/app/bus/pos_bus_service";

patch(PosBus.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.busService.subscribe("VIVA_WALLET_LATEST_RESPONSE", (payload) => {
            if (payload === this.pos.config.id) {
                this.pos
                    .getPendingPaymentLine("viva_wallet")
                    .payment_method.payment_terminal.handleVivaWalletStatusResponse();
            }
        });
    },
});
