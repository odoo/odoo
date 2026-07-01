import { ProductTemplate } from "@point_of_sale/../tests/unit/data/product_template.data";

ProductTemplate._records = ProductTemplate._records.map((record) =>
    record.id === 5 ? { ...record, taxes_id: [118] } : record
);
