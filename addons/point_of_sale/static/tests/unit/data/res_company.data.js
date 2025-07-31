import { webModels } from "@web/../tests/web_test_helpers";

export class ResCompany extends webModels.ResCompany {
    _name = "res.company";

    _load_pos_data_fields() {
        return [
            "id",
            "currency_id",
            "email",
            "website",
            "company_registry",
            "vat",
            "name",
            "phone",
            "partner_id",
            "country_id",
            "state_id",
            "tax_calculation_rounding_method",
            "nomenclature_id",
            "point_of_sale_use_ticket_qr_code",
            "point_of_sale_ticket_unique_code",
            "point_of_sale_ticket_portal_url_display_mode",
            "street",
            "city",
            "zip",
            "account_fiscal_country_id",
        ];
    }

    _records = [
        ...webModels.ResCompany._records,
        {
            id: 250,
            currency_id: 1,
            email: false,
            website: false,
            company_registry: false,
            vat: false,
            name: "My Company",
            phone: "",
            partner_id: 1,
            country_id: 233,
            state_id: false,
            tax_calculation_rounding_method: "round_per_line",
            point_of_sale_use_ticket_qr_code: true,
            point_of_sale_ticket_unique_code: false,
            point_of_sale_ticket_portal_url_display_mode: "qr_code_and_url",
            street: "",
            city: "",
            zip: "",
            account_fiscal_country_id: 233,
        },
    ];
}
