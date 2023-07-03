/** @odoo-module **/

import { registry } from "@web/core/registry";
import { many2OneBarcodeField, Many2OneBarcodeField } from "@web/views/fields/many2one_barcode/many2one_barcode_field";

export class Many2OneBarcodeFieldSaleProduct extends Many2OneBarcodeField {}

export const many2OneBarcodeFieldSaleProduct = {
    ...many2OneBarcodeField,
    component: Many2OneBarcodeField,
    extractProps(fieldInfo, dynamicInfo) {
        const props = many2OneBarcodeField.extractProps(...arguments);
        props.canOpen = dynamicInfo.context?.is_downpayment !== true && props.canOpen;
        return props;
    },
};

registry.category("fields").add("many2one_barcode_sale_product", many2OneBarcodeFieldSaleProduct);
