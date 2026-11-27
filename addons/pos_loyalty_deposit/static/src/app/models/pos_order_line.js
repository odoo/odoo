import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    delete() {
        if (this.is_reward_line) {
            this.depositLine?.delete();
        }
        return super.delete(...arguments);
    },
});
