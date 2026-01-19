import { ProductAttribute } from "@point_of_sale/../tests/unit/data/product_attribute.data";

ProductAttribute._records = [
    ...ProductAttribute._records,
    {
        id: 9,
        name: "Packaging",
        display_type: "radio",
        template_value_ids: [],
        attribute_line_ids: [],
        create_variant: "no_variant",
    },
];
