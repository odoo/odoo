import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

export class WorkcenterCapacityProduct extends Many2One {
    static template = "mrp.WorkcenterCapacityProduct";
    static components = { ...Many2One.components };
    static props = { ...Many2One.props };
}

export class WorkcenterCapacityProductField extends Component {
    static template = "mrp.WorkcenterCapacityProductField";
    static components = { WorkcenterCapacityProduct };
    static props = { ...Many2OneField.props };

    get m2oProps() {
        return computeM2OProps(this.props);
    }
}

registry.category("fields").add("mrp_workcenter_capacity_product", {
    ...buildM2OFieldDescription(WorkcenterCapacityProductField),
});
