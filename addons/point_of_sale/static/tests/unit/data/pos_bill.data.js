import { models } from "@web/../tests/web_test_helpers";

export class PosBill extends models.ServerModel {
    _name = "pos.bill";

    _load_pos_data_fields() {
        return ["id", "name", "value"];
    }

    _records = [
        {
            id: 1,
            name: "0.05",
            value: 0.05,
        },
        {
            id: 2,
            name: "0.10",
            value: 0.1,
        },
        {
            id: 3,
            name: "0.20",
            value: 0.2,
        },
        {
            id: 4,
            name: "0.25",
            value: 0.25,
        },
        {
            id: 5,
            name: "0.50",
            value: 0.5,
        },
        {
            id: 6,
            name: "1.00",
            value: 1.0,
        },
        {
            id: 7,
            name: "2.00",
            value: 2.0,
        },
        {
            id: 8,
            name: "5.00",
            value: 5.0,
        },
        {
            id: 9,
            name: "10.00",
            value: 10.0,
        },
        {
            id: 10,
            name: "20.00",
            value: 20.0,
        },
        {
            id: 11,
            name: "50.00",
            value: 50.0,
        },
        {
            id: 12,
            name: "100.00",
            value: 100.0,
        },
        {
            id: 13,
            name: "200.00",
            value: 200.0,
        },
    ];
}
