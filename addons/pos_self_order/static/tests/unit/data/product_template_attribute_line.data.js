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
    {
        id: 200,
        attribute_id: 200,
        product_template_value_ids: [200, 201, 202],
    },
    {
        id: 201,
        attribute_id: 201,
        product_template_value_ids: [203, 204],
    },
    {
        id: 202,
        attribute_id: 202,
        product_template_value_ids: [205, 206],
    },
    {
        id: 203,
        attribute_id: 203,
        product_template_value_ids: [207, 208],
    },
    {
        id: 204,
        attribute_id: 204,
        product_template_value_ids: [209],
    },
    {
        id: 205,
        attribute_id: 205,
        product_template_value_ids: [211, 212],
    },
    {
        id: 206,
        attribute_id: 204,
        product_template_value_ids: [210],
    },
    {
        id: 207,
        attribute_id: 205,
        product_template_value_ids: [211, 212],
    },
];
