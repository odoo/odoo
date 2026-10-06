import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    initState() {
        super.initState();
        this.uiState = {
            ...this.uiState,
            askedRewards: this.uiState.askedRewards || new Set(),
        };
    },
    serializeForORM(opts = {}) {
        const data = super.serializeForORM(...arguments);
        // Proof that the client identified as the order's partner, see pos.order._check_pos_order
        const token = this.partner_id?._self_order_token;
        if (token) {
            data.partner_token = token;
        }
        return data;
    },
    setPartner(partner) {
        let partnerToRemove = false;
        if (this.config._self_order_pos && partner != this.partner_id) {
            partnerToRemove = this.partner_id;
        }
        super.setPartner(...arguments);
        if (partnerToRemove) {
            this.models["loyalty.card"]
                .filter((card) => card.partner_id.id === partnerToRemove.id)
                .forEach((card) => card.delete());
            this.models["res.partner"].delete(partnerToRemove);
        }
    },
});
