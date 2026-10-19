import { ProductAttribute } from "@point_of_sale/../tests/unit/data/product_attribute.data";

ProductAttribute._records = [
    ...ProductAttribute._records,
    {
        id: 20,
        name: "Archived Size",
        display_type: "radio",
        create_variant: "no_variant",
    },
];
