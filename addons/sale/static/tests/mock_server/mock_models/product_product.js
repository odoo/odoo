import { models } from "@web/../tests/web_test_helpers";


export class ProductProduct extends models.ServerModel {
    _name = "product.product";

    _records = [
        {id: 1, name: "Test Product", type: "consu", list_price: 20.0},
        {id: 2, name: "Test Service Product", type: "service", list_price: 50.0},
    ];
}
