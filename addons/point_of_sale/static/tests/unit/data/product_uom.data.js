import { models } from "@web/../tests/web_test_helpers";

export class ProductUom extends models.ServerModel {
    _name = "product.uom";

    _load_pos_data_fields() {
        return ["id", "barcode", "product_id", "uom_id"];
    }
}
