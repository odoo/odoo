/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosBus } from "@point_of_sale/app/bus/pos_bus_service";

patch(PosBus.prototype, {
    // Override
    dispatch(message) {
        super.dispatch(...arguments);
        if (message.type === "MERCADO_PAGO_LATEST_MESSAGE") {
            this.pos
                .getPendingPaymentLine("mercado_pago")
                .payment_method.payment_terminal.handleMercadoPagoWebhook();
        }
    },
});
