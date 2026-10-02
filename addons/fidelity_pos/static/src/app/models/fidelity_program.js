import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";

export class FidelityProgram extends Base {
    static pythonModel = "fidelity.program";

    setup(vals) {
        super.setup(vals);
    }

    initState() {
        super.initState();
        this.uiState = {};
    }

    redeemablePoints(order) {
        return this.rule_ids.reduce((total, rule) => total + rule.redeemablePoints(order), 0);
    }
}

registry.category("pos_available_models").add(FidelityProgram.pythonModel, FidelityProgram);
