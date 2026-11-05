import { registry } from "@web/core/registry";
import * as numbers from "@point_of_sale/app/utils/numbers";

export class UomUom extends numbers.AbstractNumbers {
    static pythonModel = "uom.uom";

    getFactorTo(baseUom) {
        if (!baseUom || this.id === baseUom.id) {
            return 1;
        }
        return this.factor / baseUom.factor;
    }
}

registry.category("pos_available_models").add(UomUom.pythonModel, UomUom);
