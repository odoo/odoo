/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc";
import { handleRPCError } from "@point_of_sale/app/errors/error_handlers";

patch(PaymentScreen.prototype, {
    async _postPushOrderResolve(order, _order_server_ids) {
        if (this.pos.company.l10n_es_edi_verifactu_required) {
            try {
                order.invoice_name = await this.pos.data.call(
                    "pos.order",
                    "l10n_es_edi_verifactu_get_invoice_name",
                    [order.id]
                );
            } catch (error) {
                if (error instanceof ConnectionLostError) {
                    return false;
                } else if (error instanceof RPCError) {
                    handleRPCError(error, this.dialog);
                } else {
                    throw error;
                }
            }
        }
        return super._postPushOrderResolve(...arguments);
    },
});
