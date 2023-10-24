/** @odoo-module **/

import { productField, ProductField } from "@product/js/product_configurator/product_configurator_field";
import { registry } from "@web/core/registry";

export class StockProductField extends ProductField
{
    get productUomFieldName() {
        return 'product_uom';
    }
}

export const stockProductField = {
    ...productField,
    component: StockProductField,
};

registry.category("fields").add("stock_product_many2one", stockProductField);
