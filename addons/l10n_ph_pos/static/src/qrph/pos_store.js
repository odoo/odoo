import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";

patch(PosStore.prototype, {
    async showQR(payment) {
        // Tell the server which order the code is minted for, so that the payment it opens on Maya
        // can be tied back to the order when the cashier confirms it.
        user.updateContext({
            l10n_ph_qrph_model: "pos.order",
            l10n_ph_qrph_model_id: payment.pos_order_id.uuid,
        });
        try {
            return await super.showQR(payment);
        } finally {
            // The user context lives as long as the session, and the next code may well be minted
            // for something else entirely.
            user.updateContext({ l10n_ph_qrph_model: false, l10n_ph_qrph_model_id: false });
        }
    },
});
