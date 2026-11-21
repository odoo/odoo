import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { compareProductsByFavoriteAndSequence } from "@point_of_sale/utils";

export class ProductCombo extends Base {
    static pythonModel = "product.combo";

    get sortedComboItems() {
        return this.combo_item_ids
            .filter((item) => item.product_id)
            .sort((a, b) => compareProductsByFavoriteAndSequence(a.product_id, b.product_id));
    }
}

registry.category("pos_available_models").add(ProductCombo.pythonModel, ProductCombo);
