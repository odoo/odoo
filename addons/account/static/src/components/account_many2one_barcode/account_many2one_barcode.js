import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    Many2OneField,
} from "@web/views/fields/many2one/many2one_field";

export class AccountMany2oneBarcode extends Component {
    static template = "account.AccountMany2oneBarcode";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    get m2oProps() {
        return {
            ...computeM2OProps(this.props),
        };
    }

    get hasExternalButton() {
        // Inspired by sol_product_many2one to display external button despite no_open
        const res = super.hasExternalButton;
        return res || (!!this.props.record.data[this.props.name] && !this.state.isFloating);
    }
}

registry.category("fields").add("account_many2one_barcode", {
    ...buildM2OFieldDescription(AccountMany2oneBarcode),
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            canScanBarcode: true,
        };
    },
});
