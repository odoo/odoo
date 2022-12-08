/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneField } from '@web/views/fields/many2one/many2one_field';


export class ProductPackagingWidget extends Many2OneField {
    get displayName() {
        const displayName = super.displayName;
        if (this.context.product_packaging_qty > 0) {
            return displayName + "(×" + this.context.product_packaging_qty + ")";
        }
        return displayName;
    }

    get hasExternalButton() {
        // Keep external button, even if field is specified as 'no_open' so that the user is not
        // redirected to the packaging when clicking on the field content
        const res = super.hasExternalButton;
        return res || (!!this.props.value && !this.state.isFloating);
    }
}

registry.category("fields").add("product_packaging_widget", ProductPackagingWidget);
