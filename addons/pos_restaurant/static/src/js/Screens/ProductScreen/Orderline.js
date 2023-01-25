/** @odoo-module */

import { Orderline } from "@point_of_sale/js/Screens/ProductScreen/Orderline";
import { patch } from "@web/core/utils/patch";

patch(Orderline.prototype, "pos_restaurant.Orderline", {
    /**
     * @override
     */
    get addedClasses() {
        const res = this._super(...arguments);
        Object.assign(res, {
            dirty: this.props.line.mp_dirty,
            skip: this.props.line.mp_skip,
        });
        return res;
    },
    /**
     * @override
     * if doubleclick, change mp_dirty to mp_skip
     *
     * IMPROVEMENT: Instead of handling both double click and click in single
     * method, perhaps we can separate double click from single click.
     */
    selectLine() {
        const line = this.props.line; // the orderline
        if (this.env.pos.get_order().selected_orderline.id !== line.id) {
            this.mp_dbclk_time = new Date().getTime();
        } else if (!this.mp_dbclk_time) {
            this.mp_dbclk_time = new Date().getTime();
        } else if (this.mp_dbclk_time + 500 > new Date().getTime()) {
            line.set_skip(!line.mp_skip);
            this.mp_dbclk_time = 0;
        } else {
            this.mp_dbclk_time = new Date().getTime();
        }
        this._super(...arguments);
    },
});
