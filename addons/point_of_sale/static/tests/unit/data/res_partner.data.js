import { ResPartner as MailResPartner } from "@mail/../tests/mock_server/mock_models/res_partner";

export class ResPartner extends MailResPartner {
    _name = "res.partner";

    _load_pos_data_fields() {
        return [
            "id",
            "name",
            "street",
            "street2",
            "city",
            "state_id",
            "country_id",
            "vat",
            "lang",
            "phone",
            "zip",
            "email",
            "barcode",
            "write_date",
            "property_product_pricelist",
            "parent_name",
            "pos_contact_address",
            "invoice_emails",
            "company_type",
            "fiscal_position_id",
        ];
    }

    _records = [
        ...MailResPartner.prototype.constructor._records,
        {
            id: 3,
            name: "Administrator",
            street: false,
            street2: false,
            city: false,
            state_id: false,
            country_id: false,
            vat: false,
            lang: "en_US",
            phone: false,
            zip: false,
            email: false,
            barcode: false,
            write_date: "2025-07-03 12:38:12",
            property_product_pricelist: false,
            parent_name: false,
            pos_contact_address: "\n\n  \n",
            invoice_emails: "",
            company_type: "person",
            fiscal_position_id: false,
            credit_limit: 0.0,
            use_partner_credit_limit: false,
        },
    ];
}
