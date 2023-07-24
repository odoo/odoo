/** @odoo-module **/
import { Reactive } from "@web/core/utils/reactive";
import { ComboLine } from "./combo_line";

export class Combo extends Reactive {
    constructor({ id, name, combo_line_ids }) {
        super();
        this.setup(...arguments);
    }

    setup(combo) {
        // server only data (recovered after first send to server)
        this.id = combo.id || null;
        this.name = combo.name || null;
        this.combo_line_ids = combo.combo_line_ids || [];
        this.initLines();
    }

    initLines() {
        this.combo_line_ids = this.combo_line_ids.map((line) => new ComboLine(line));
    }
}
