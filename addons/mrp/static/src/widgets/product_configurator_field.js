/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductField } from "@product/js/product_configurator/product_configurator_field";

patch(ProductField.prototype, {
    get quantityFieldName() {
        if (this.props.record.model.config.resModel === 'mrp.production') {
            return 'product_qty';
        } else {
            return super.quantityFieldName;
        }
    }
});
