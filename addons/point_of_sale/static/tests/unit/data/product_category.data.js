import { models } from "@web/../tests/web_test_helpers";

export class ProductCategory extends models.ServerModel {
    _name = "product.category";

    _load_pos_data_fields() {
        return ["id", "name", "parent_id"];
    }

    _records = [
        {
            id: 2,
            name: "Expenses",
            parent_id: false,
        },
        {
            id: 4,
            name: "Food",
            parent_id: false,
        },
        {
            id: 1,
            name: "Goods",
            parent_id: false,
        },
        {
            id: 3,
            name: "Services",
            parent_id: false,
        },
    ];
}
