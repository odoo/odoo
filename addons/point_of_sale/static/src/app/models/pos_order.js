/** @odoo-module */
import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class PosOrder extends Base {
    static pythonModel = "pos.order";
}

registry.category("pos_available_models").add(PosOrder.pythonModel, PosOrder);
