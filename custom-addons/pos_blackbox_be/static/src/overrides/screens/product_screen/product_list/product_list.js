/** @odoo-module **/

import { ProductsWidget } from "@point_of_sale/app/screens/product_screen/product_list/product_list";
import { patch } from "@web/core/utils/patch";

patch(ProductsWidget.prototype, {
    getCategories() {
        const result = super.getCategories(...arguments);
        if (this.pos.useBlackBoxBe()) {
            const fiscal_data_category = this.pos.workInProduct.pos_categ_ids[0];
            return result.filter((category) => category.id !== fiscal_data_category);
        }
        return result;
    },
});
