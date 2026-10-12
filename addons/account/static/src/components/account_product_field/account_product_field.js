import { registry } from "@web/core/registry";
import { Component, useProps } from "@odoo/owl";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    many2OneFieldProps,
} from "@web/views/fields/many2one/many2one_field";

export class AccountProductField extends Component {
    static template = "account.AccountProductField";
    static components = { Many2One };
    props = useProps(many2OneFieldProps);

    get isProductClickable() {
        return this.props.record.evalContext.parent.state !== "draft";
    }

    get m2oProps() {
        const props = computeM2OProps(this.props);
        return {
            ...props,
            canOpen: props.canOpen && (!this.props.readonly || this.isProductClickable),
            preventMemoization: true,
        };
    }
}

export const accountProductField = { ...buildM2OFieldDescription(AccountProductField) };

registry.category("fields").add("account_product_field", accountProductField);
