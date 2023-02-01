/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Chrome } from "@point_of_sale/js/Chrome";

patch(Chrome.prototype, "pos_restaurant.Chrome", {
    /**
     * @override
     * FIXME POSREF move to pos store
     * `FloorScreen` is the start screen if there are floors.
     */
    get startScreen() {
        if (this.env.pos.config.iface_floorplan) {
            const table = this.env.pos.table;
            return { name: "FloorScreen", props: { floor: table ? table.floor : null } };
        } else {
            return this._super(...arguments);
        }
    },
});
