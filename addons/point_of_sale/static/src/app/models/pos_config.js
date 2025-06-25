import { registry } from "@web/core/registry";
import { Base } from "./related_models";

// Overrided in blackbox BE
export class PosConfig extends Base {
    static pythonModel = "pos.config";
}

registry.category("pos_available_models").add(PosConfig.pythonModel, PosConfig);
