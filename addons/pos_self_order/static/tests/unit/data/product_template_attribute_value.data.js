import { ProductTemplateAttributeValue } from "@point_of_sale/../tests/unit/data/product_template_attribute_value.data";

ProductTemplateAttributeValue._records = [
    ...ProductTemplateAttributeValue._records,
    {
        id: 1,
        name: "S",
        attribute_id: 7,
    },
    {
        id: 2,
        name: "M",
        attribute_id: 7,
    },
];
