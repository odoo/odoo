/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneBarcodeField, many2OneBarcodeField } from "@web/views/fields/many2one_barcode/many2one_barcode_field";

export class AccountMany2oneBarcode extends Many2OneBarcodeField {
    get hasExternalButton() {
        // Inspired by sol_product_many2one to display external button despite no_open
        const res = super.hasExternalButton;
        return res || (!!this.props.record.data[this.props.name] && !this.state.isFloating);
    }
}

registry.category("fields").add("account_many2one_barcode", {
    ...many2OneBarcodeField,
    component: AccountMany2oneBarcode,
});
