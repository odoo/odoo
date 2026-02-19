import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";

export class FidelityTransaction extends Base {
    static pythonModel = "fidelity.transaction";

    setup(vals) {
        super.setup(vals);
    }

    initState() {
        super.initState();
        this.uiState = {};
    }
}

registry.category("pos_available_models").add(FidelityTransaction.pythonModel, FidelityTransaction);
