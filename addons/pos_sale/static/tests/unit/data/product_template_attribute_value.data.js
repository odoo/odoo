import { ProductTemplateAttributeValue } from "@point_of_sale/../tests/unit/data/product_template_attribute_value.data";

ProductTemplateAttributeValue._records = [
    ...ProductTemplateAttributeValue._records,
    {
        id: 20,
        name: "S",
        attribute_id: 20,
        attribute_line_id: 8,
    },
    {
        id: 21,
        name: "M",
        attribute_id: 20,
        attribute_line_id: 8,
    },
];
