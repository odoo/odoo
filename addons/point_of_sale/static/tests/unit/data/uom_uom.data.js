import { models } from "@web/../tests/web_test_helpers";

export class UomUom extends models.ServerModel {
    _name = "uom.uom";

    _load_pos_data_fields() {
        return ["id", "name", "factor", "is_pos_groupable", "parent_path"];
    }

    _records = [
        {
            id: 5,
            name: "Days",
            factor: 8.0,
            is_pos_groupable: false,
            parent_path: "4/5/",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 2,
            name: "Pack of 6",
            factor: 6.0,
            is_pos_groupable: true,
            parent_path: "1/2/",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 8,
            name: "m",
            factor: 1000.0,
            is_pos_groupable: false,
            parent_path: "6/7/8/",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 15,
            name: "kg",
            factor: 1000.0,
            is_pos_groupable: false,
            parent_path: "14/15/",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 16,
            name: "Ton",
            factor: 1000000.0,
            is_pos_groupable: false,
            parent_path: "14/15/16/",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 12,
            name: "L",
            factor: 1000.0,
            is_pos_groupable: false,
            parent_path: "11/12/",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 4,
            name: "Hours",
            factor: 1.0,
            is_pos_groupable: false,
            parent_path: "4/",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 1,
            name: "Units",
            factor: 1.0,
            is_pos_groupable: true,
            parent_path: "1/",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 14,
            name: "g",
            factor: 1.0,
            is_pos_groupable: false,
            parent_path: "14/",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 11,
            name: "ml",
            factor: 1.0,
            is_pos_groupable: false,
            parent_path: "11/",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 6,
            name: "mm",
            factor: 1.0,
            is_pos_groupable: false,
            parent_path: "6/",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 10,
            name: "m²",
            factor: 1.0,
            is_pos_groupable: false,
            parent_path: "10/",
            write_date: "2025-01-01 10:00:00",
        },
    ];
}
