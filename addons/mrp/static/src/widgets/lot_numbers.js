/** @odoo-module */

import { registry } from "@web/core/registry";
import { Field } from "@web/views/fields/field";


export class LotNumbers extends Field {
    setup() {
        super.setup();
        this.set_placeholder();
    }

    set_placeholder() {
        if (!this.props.record.evalContext.from_generate_sn_wizard){
            this.props['placeholder'] = this.props.record.data.lot_numbers;
            this.props.record.data.lot_numbers = "";
        }
    }
}

registry.category("fields").add("lot_numbers", {
    component: LotNumbers,
});
