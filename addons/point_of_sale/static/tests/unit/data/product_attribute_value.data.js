import { models } from "@web/../tests/web_test_helpers";

export class ProductAttributeValue extends models.ServerModel {
    _name = "product.attribute.value";

    _records = [
        {
            id: 1,
            name: "White",
            attribute_id: 1,
        },
        {
            id: 2,
            name: "Black",
            attribute_id: 1,
        },
        {
            id: 3,
            name: "Blue",
            attribute_id: 1,
            default_extra_price: 5.0,
        },
    ];
}
