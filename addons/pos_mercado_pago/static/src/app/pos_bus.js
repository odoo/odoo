/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosBus } from "@point_of_sale/app/bus/pos_bus_service";

patch(PosBus.prototype, {
    // Override
    setup() {
        super.setup(...arguments);
        this.busService.subscribe("MERCADO_PAGO_LATEST_MESSAGE", (payload) => {
            if (payload.config_id === this.pos.config.id) {
                this.pos
                    .getPendingPaymentLine("mercado_pago")
                    .payment_method.payment_terminal.handleMercadoPagoWebhook();
            }
        });
    },
});
