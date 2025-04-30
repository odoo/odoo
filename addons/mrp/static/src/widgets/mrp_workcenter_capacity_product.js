import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { createMany2OneValue } from "@web/model/relational_model/utils";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

export class WorkcenterCapacityProduct extends Many2One {

    get value() {
        let result = super.value;
        if (result === null && this.props.readonly) {
            result = createMany2OneValue([false, this.props.placeholder]);
        }
        return result;
    }
}

export class WorkcenterCapacityProductField extends Component {
    static template = "web.Many2OneField";
    static components = { Many2One: WorkcenterCapacityProduct };
    static props = { ...Many2OneField.props };

    get m2oProps() {
        return computeM2OProps(this.props);
    }
}

registry.category("fields").add("mrp_workcenter_capacity_product", {
    ...buildM2OFieldDescription(WorkcenterCapacityProductField),
});
