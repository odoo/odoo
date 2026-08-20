import { models } from "@web/../tests/web_test_helpers";

export class ProductTag extends models.ServerModel {
    _name = "product.tag";

    _load_pos_data_fields() {
        return ["name", "pos_description", "color", "has_image", "write_date"];
    }

    _records = [
        {
            id: 1001,
            name: "Red tag",
            color: "#ff0000",
        },
        {
            id: 1002,
            name: "Blue tag",
            color: "#0000ff",
        },
    ];
}
