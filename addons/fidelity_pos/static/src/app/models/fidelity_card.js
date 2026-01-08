import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";

export class FidelityCard extends Base {
    static pythonModel = "fidelity.card";

    setup(vals) {
        super.setup(vals);
    }

    initState() {
        super.initState();
        this.uiState = {};
    }
}

registry.category("pos_available_models").add(FidelityCard.pythonModel, FidelityCard);
