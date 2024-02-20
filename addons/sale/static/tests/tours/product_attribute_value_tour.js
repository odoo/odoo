import { registry } from "@web/core/registry";

const openProductAttribute = (product_attribute) => [
    {
        content: 'Open sale app',
        trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    },
    {
        content: 'Open configuration menu',
        trigger: '.o-dropdown[data-menu-xmlid="sale.menu_sale_config"]',
    },
    {
        content: 'Navigate to product attribute list view',
        trigger: '.o-dropdown-item[data-menu-xmlid="sale.menu_product_attribute_action"]',
    },
    {
        content: `Navigate to ${product_attribute}`,
        trigger: `.o_data_cell[data-tooltip=${product_attribute}]`,
    },
];
const deletePAV = (product_attribute_value, message) => [
    {
        content: 'Click delete button',
        trigger: `.o_data_cell[data-tooltip=${product_attribute_value}] ~ .o_list_record_remove`,
    },
    {
        content: 'Check correct message in modal',
        trigger: message || '.modal-title:contains("Bye-bye, record!")',
    },
    {
        content: 'Close modal',
        trigger: '.btn-close',
    }
]

// This tour relies on data created on the Python test.
registry.category("web_tour.tours").add('delete_product_attribute_value_tour', {
    url: '/odoo',
    test: true,
    steps: () => [
        ...openProductAttribute("PA"),
        // Test error message on a used attribute value
        ...deletePAV("pa_value_1", ".text-prewrap:contains('pa_value_1')"),
        // Test deletability of a used attribute value on archived product
        ...deletePAV("pa_value_2"),
        // Test deletability of a removed attribute value on product
        ...deletePAV("pa_value_3"),
        {
            content: 'Check test finished',
            trigger: 'a:contains("Attributes")',
            run: () => { }, // check
        }
    ]
});
