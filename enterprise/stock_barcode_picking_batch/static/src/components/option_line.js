/** @odoo-module **/

import { Component } from "@odoo/owl";

export default class OptionLine extends Component {
    static props = ["line", "additionalClass?", "responsible?"];
    static template = "stock_barcode_picking_batch.OptionLine";
    get isSelected() {
        if (this.env.model.needPickingType) {
            return this.env.model.selectedPickingTypeId === this.props.line.id;
        } else if (this.env.model.needPickings) {
            return this.env.model.selectedPickings.indexOf(this.props.line.id) !== -1;
        }
    }

    select() {
        this.env.model.selectOption(this.props.line.id);
    }
}
