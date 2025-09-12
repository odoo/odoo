import { models } from "@web/../tests/web_test_helpers";


export class ProductTemplate extends models.ServerModel {
    _name = "product.template";

    get_single_product_variant() {
        return { product_id: 14, product_name: "desk" };
    }

    _records = [{ id: 12, name: "desk" }];
}
