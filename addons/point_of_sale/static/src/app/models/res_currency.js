import { registry } from "@web/core/registry";
import * as numbers from "@point_of_sale/app/utils/numbers";

export class ResCurrency extends numbers.AbstractNumbers {
    static pythonModel = "res.currency";
    get precision() {
        return this.rounding;
    }
}

registry.category("pos_available_models").add(ResCurrency.pythonModel, ResCurrency);
