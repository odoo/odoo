import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen.prototype, {
    getCategoriesAndSub() {
        const result = super.getCategoriesAndSub(...arguments);
        if (this.pos.useBlackBoxBe()) {
            const fiscal_data_category = this.pos.config.work_in_product.pos_categ_ids[0];
            return result.filter((category) => category.id !== fiscal_data_category.id);
        }
        return result;
    },
});
