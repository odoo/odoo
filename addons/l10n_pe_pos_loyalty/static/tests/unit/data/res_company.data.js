import { ResCompany } from "@point_of_sale/../tests/unit/data/res_company.data";

ResCompany._records = ResCompany._records.map((record) =>
    record.id === 250 ? { ...record, country_id: 604, account_fiscal_country_id: 604 } : record
);
