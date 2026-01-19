import { ProductTemplateAttributeValue } from "@point_of_sale/../tests/unit/data/product_template_attribute_value.data";

ProductTemplateAttributeValue._records = [
    ...ProductTemplateAttributeValue._records,
    {
        id: 101,
        name: "S",
        attribute_id: 7,
    },
    {
        id: 102,
        name: "M",
        attribute_id: 7,
    },
];
