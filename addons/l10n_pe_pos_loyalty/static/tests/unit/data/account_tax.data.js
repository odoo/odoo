import { AccountTax } from "@point_of_sale/../tests/unit/data/account_tax.data";

AccountTax._records = [
    ...AccountTax._records,
    {
        id: 118,
        name: "IGV 18%",
        price_include: false,
        include_base_amount: false,
        is_base_affected: true,
        has_negative_factor: false,
        amount_type: "percent",
        children_tax_ids: [],
        amount: 18.0,
        company_id: 250,
        sequence: 1,
        tax_group_id: 1,
        fiscal_position_ids: [],
    },
];
