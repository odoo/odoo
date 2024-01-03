/** @odoo-module */
import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class PosStoreBridge extends Base {
    // this is a dummy models, created to have
    // access to his data directly from others models
    static pythonModel = "pos.store";

    setup() {
        super.setup(...arguments);
        this.pos = null;
    }

    init(pos) {
        this.pos = pos;
    }
}

registry.category("pos_available_models").add(PosStoreBridge.pythonModel, PosStoreBridge);
