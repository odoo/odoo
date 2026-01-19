import { ProductTemplateAttributeLine } from "@point_of_sale/../tests/unit/data/product_template_attribute_line.data";

ProductTemplateAttributeLine._records = [
    ...ProductTemplateAttributeLine._records,
    {
        id: 1,
        attribute_id: 7,
        product_template_value_ids: [1, 2],
    },
    {
        id: 2,
        attribute_id: 9,
        product_template_value_ids: [3, 4],
    },
];
