import { ProductAttributeCustomValue } from "@point_of_sale/../tests/unit/data/product_attribute_custom_value.data";

ProductAttributeCustomValue._records = [
    ...(ProductAttributeCustomValue._records || []),
    {
        id: 1,
        custom_value: "Value",
        custom_product_template_attribute_value_id: 7,
    },
];
