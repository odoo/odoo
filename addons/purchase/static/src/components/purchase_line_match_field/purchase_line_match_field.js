import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

export class PurchaseLineMatchField extends Component {
    static components = { Many2One };
    static props = { ...Many2OneField.props };
    static template = "purchase.PurchaseLineMatchField";

    get m2oProps() {
        const props = computeM2OProps(this.props);

        const value = props.value && { ...props.value };
        if (value && this.data.purchase_matching_issue_msg) {
            value.display_name = value.display_name + this.data.purchase_matching_issue_msg;
        }

        return {
            ...props,
            value,
        };
    }

    get data() {
        return this.props.record.data;
    }
}

registry.category("fields").add("purchase_line_match_field", {
    ...buildM2OFieldDescription(PurchaseLineMatchField),
    fieldDependencies: [{ name: "purchase_matching_issue_msg", type: "string" }],
});
