/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class Orderline extends Component {
    static template = "point_of_sale.Orderline";

    /**
     * if doubleclick, change hasChange to skipChange
     *
     * IMPROVEMENT: Instead of handling both double click and click in single
     * method, perhaps we can separate double click from single click.
     */
    setup() {
        this.pos = usePos();
    }
    selectLine() {
        const line = this.props.line; // the orderline
        if (this.pos.get_order().selected_orderline.id !== line.id) {
            this.mp_dbclk_time = new Date().getTime();
        } else if (!this.mp_dbclk_time) {
            this.mp_dbclk_time = new Date().getTime();
        } else if (this.mp_dbclk_time + 500 > new Date().getTime()) {
            line.toggleSkipChange();
            this.mp_dbclk_time = 0;
        } else {
            this.mp_dbclk_time = new Date().getTime();
        }

        this.props.selectLine(this.props.line);
    }
    lotIconClicked() {
        this.props.editPackLotLines(this.props.line);
    }
    get addedClasses() {
        return {
            selected: this.props.line.selected,
            "has-change":
                this.props.line.hasChange && this.pos.config.module_pos_restaurant,
            "skip-change":
                this.props.line.skipChange && this.pos.config.module_pos_restaurant,
        };
    }
    get customerNote() {
        return this.props.line.get_customer_note();
    }
}
