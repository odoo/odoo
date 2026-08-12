import { ProductTemplateAttributeLine } from "@point_of_sale/../tests/unit/data/product_template_attribute_line.data";

ProductTemplateAttributeLine._records = [
    ...ProductTemplateAttributeLine._records,
    {
        id: 8,
        attribute_id: 20,
        product_template_value_ids: [20, 21],
        active: false,
    },
];
