import { ResCompany } from "@point_of_sale/../tests/unit/data/res_company.data";

// The company of the point_of_sale test data, which the POS configs of the tests belong to.
const posCompany = ResCompany._records.find((company) => company.id === 250);

ResCompany._records = [
    ...ResCompany._records,
    {
        // A Spanish company, based on the one of point_of_sale so that its fields stay valid.
        ...posCompany,
        id: 254,
        name: "My ES Company",
        country_id: 68,
        account_fiscal_country_id: 68,
    },
];
