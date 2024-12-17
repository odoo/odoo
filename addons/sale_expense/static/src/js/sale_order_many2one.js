import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Many2One, useMany2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

export class OrderField extends Component {
    static template = "sale_expense.OrderField";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    setup() {
        this.m2o = useMany2One(() => this.props);
    }

    get m2oProps() {
        return {
            ...this.m2o.computeProps(),
            canSearchMore: false,
        };
    }
}

registry.category("fields").add("sale_order_many2one", {
    ...buildM2OFieldDescription(OrderField),
});
