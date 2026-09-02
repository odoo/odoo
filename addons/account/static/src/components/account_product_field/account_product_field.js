import { _t } from "@web/core/l10n/translation";
import {
    buildM2OFieldDescription,
    many2OneFieldProps,
} from "@web/views/fields/many2one/many2one_field";
import { registry } from "@web/core/registry";
import { Component, useProps } from "@odoo/owl";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";

export class AccountProductField extends Component {
    static template = "account.AccountProductField";
    static components = { Many2One };
    props = useProps(many2OneFieldProps);

    get isProductClickable() {
        return this.props.record.evalContext.parent.state !== "draft";
    }

    get m2oProps() {
        const p = computeM2OProps(this.props);
        return {
            ...p,
            canOpen: p.canOpen && (!this.props.readonly || this.isProductClickable),
            preventMemoization: true,
        };
    }
}

export const accountProductField = {
    ...buildM2OFieldDescription(AccountProductField),
    listViewWidth: [240, 400],
};

registry.category("fields").add("account_product_field", accountProductField);
