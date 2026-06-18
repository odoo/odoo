import { PosData } from "@point_of_sale/app/services/data_service";
import { patch } from "@web/core/utils/patch";

patch(PosData.prototype, {
    async initData(...args) {
        await super.initData(...args);
        this.sanitizeData();
    },
    /**
     * Drop cached orders holding a stale reward line (no card, no reward), e.g.
     * orders kept in IndexedDB across an upgrade that changed the reward model.
     */
    sanitizeData() {
        const order_to_delete = this.models["pos.order"].filter((order) =>
            order.lines.some((line) => line.is_reward_line && !line.card_id && !line.reward_id)
        );
        for (const order of order_to_delete) {
            for (let i = order.lines.length - 1; i >= 0; i--) {
                order.lines[i].delete();
            }
        }
    },
});
