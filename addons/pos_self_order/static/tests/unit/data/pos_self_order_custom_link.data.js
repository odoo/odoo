import { models } from "@web/../tests/web_test_helpers";

export class PosSelfOrderCustomLink extends models.ServerModel {
    _name = "pos_self_order.custom_link";

    _load_pos_data_fields() {
        return ["id", "name", "style", "sequence", "url", "link_html"];
    }

    _records = [
        {
            id: 1,
            name: "Order Now",
            style: "primary",
            sequence: 1,
            url: "/pos-self/1/products",
            link_html: "<a class='btn btn-primary w-100'>Order Now</a>",
        },
    ];
}
