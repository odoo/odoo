/** @odoo-module */
import { registry } from "@web/core/registry";
import { uuidv4 } from "@point_of_sale/utils";
import { Base } from "./related_models";

export class PosOrderline extends Base {
    static pythonModel = "pos.order.line";

    setup(vals) {
        super.setup(vals);
        this.uuid = vals.uuid ? vals.uuid : uuidv4();
    }
}

registry.category("pos_available_models").add(PosOrderline.pythonModel, PosOrderline);
