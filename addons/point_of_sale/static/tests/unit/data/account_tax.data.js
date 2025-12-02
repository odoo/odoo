import { models } from "@web/../tests/web_test_helpers";

export class AccountTax extends models.ServerModel {
    _name = "account.tax";

    _load_pos_data_fields() {
        return [
            "id",
            "name",
            "price_include",
            "include_base_amount",
            "is_base_affected",
            "has_negative_factor",
            "amount_type",
            "children_tax_ids",
            "amount",
            "company_id",
            "id",
            "sequence",
            "tax_group_id",
        ];
    }

    _records = [
        {
            id: 1,
            name: "15%",
            price_include: false,
            include_base_amount: false,
            is_base_affected: true,
            has_negative_factor: false,
            amount_type: "percent",
            children_tax_ids: [],
            amount: 15.0,
            company_id: 250,
            sequence: 1,
            tax_group_id: 1,
        },
        {
            id: 2,
            name: "25%",
            price_include: false,
            include_base_amount: false,
            is_base_affected: true,
            has_negative_factor: false,
            amount_type: "percent",
            children_tax_ids: [],
            amount: 25.0,
            company_id: 250,
            sequence: 1,
            tax_group_id: 3,
        },
        {
            id: 3,
            name: "tax incl",
            type_tax_use: "sale",
            amount_type: "percent",
            amount: 7,
            price_include_override: "tax_included",
            include_base_amount: true,
            has_negative_factor: true,
            company_id: 250,
            is_base_affected: true,
            tax_group_id: 4,
        },
    ];
}
