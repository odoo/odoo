/** @odoo-module **/
import { Reactive } from "@web/core/utils/reactive";

export class ComboLine extends Reactive {
    constructor({ id, lst_price, combo_price, product_id, combo_id }) {
        super();
        this.setup(...arguments);
    }

    setup(comboLine) {
        // server only data (recovered after first send to server)
        this.id = comboLine.id || null;
        this.lst_price = comboLine.lst_price || null;
        this.combo_price = comboLine.combo_price || null;
        this.product_id = comboLine.product_id || null;
        this.combo_id = comboLine.combo_id || null;
    }
}
