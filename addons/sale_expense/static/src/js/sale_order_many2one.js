import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

export class OrderField extends Component {
    static template = "sale_expense.OrderField";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    get m2oProps() {
        return {
            ...computeM2OProps(this.props),
            canSearchMore: false,
        };
    }
}

registry.category("fields").add("sale_order_many2one", {
    ...buildM2OFieldDescription(OrderField),
});
