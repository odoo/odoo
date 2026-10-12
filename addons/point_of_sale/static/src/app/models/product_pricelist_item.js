import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class ProductPricelistItem extends Base {
    static pythonModel = "product.pricelist.item";

    setup() {
        super.setup(...arguments);
        this.pricelist_id.addRuleIndex(this, this.pricelist_id.item_ids.indexOf(this));
    }
}

registry
    .category("pos_available_models")
    .add(ProductPricelistItem.pythonModel, ProductPricelistItem);
