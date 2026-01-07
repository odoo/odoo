import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";


export class LoyaltyProgram extends Base {
    static pythonModel = "loyalty.program";

    initState() {
        super.initState();
        this.uiState = {
            linkedCard: null,
            pointsDifference: 0,
            ...this.uiState,
        };
    }
}

registry.category("pos_available_models").add(LoyaltyProgram.pythonModel, LoyaltyProgram);