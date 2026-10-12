import { registry } from "@web/core/registry";
import * as numbers from "@point_of_sale/app/utils/numbers";

export class UomUom extends numbers.AbstractNumbers {
    static pythonModel = "uom.uom";
}

registry.category("pos_available_models").add(UomUom.pythonModel, UomUom);
