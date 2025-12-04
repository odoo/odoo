import { ResCountry } from "@point_of_sale/../tests/unit/data/res_country.data";

ResCountry._records = [
    ...ResCountry._records,
    {
        id: 75,
        name: "France",
        code: "FR",
        vat_label: "VAT",
    },
];
