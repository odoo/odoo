import { ProductTemplateAttributeLine } from "@point_of_sale/../tests/unit/data/product_template_attribute_line.data";

ProductTemplateAttributeLine._records = [
    ...ProductTemplateAttributeLine._records,
    {
        id: 101,
        attribute_id: 7,
        product_template_value_ids: [101, 102],
    },
    {
        id: 102,
        attribute_id: 101,
        product_template_value_ids: [103, 104],
    },
];
