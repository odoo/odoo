import { registry } from "@web/core/registry";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";

export class WorkcenterCapacityProduct extends Many2OneField {

    get value() {
        let result = super.value;
        if (result === false && this.props.readonly) {
            result = [false, this.props.placeholder];
        }
        return result;
    }
}

export const workcenterCapacityProduct = {
    ...many2OneField,
    component: WorkcenterCapacityProduct,
};

registry.category("fields").add("mrp_workcenter_capacity_product", workcenterCapacityProduct);
