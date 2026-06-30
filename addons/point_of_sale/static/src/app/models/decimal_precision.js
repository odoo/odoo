import { registry } from "@web/core/registry";
import * as numbers from "@point_of_sale/app/utils/numbers";

export class DecimalPrecision extends numbers.AbstractNumbers {
    static pythonModel = "decimal.precision";
    get precision() {
        return Math.pow(10, -this.digits);
    }
}

registry.category("pos_available_models").add(DecimalPrecision.pythonModel, DecimalPrecision);
