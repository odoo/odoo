/** @odoo-module **/

    import { registry } from "@web/core/registry";

    // This tour relies on a data created from the python test.
    registry.category("web_tour.tours").add('tour_variants_modal_window', {
        url: '/shop?search=Short (TEST)',
        steps: () => [
        {
            content: "Select the Short (TEST) product",
            trigger: `.oe_product_cart a:contains(/^Short \\(TEST\\)$/)`,
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Click on the always variant",
            trigger: 'input[data-attribute_name="Always attribute size"][data-value_name="M always"]',
            run: "check",
        },
        {
            content: "Click on the dynamic variant",
            trigger: 'input[data-attribute_name="Dynamic attribute size"][data-value_name="M dynamic"]',
            run: "check",
        },
        {
            content: "Click on the never variant",
            trigger: 'input[data-attribute_name="Never attribute size"][data-value_name="M never"]',
            run: "check",
        },
        {
            content: "Click on the never custom variant",
            trigger: 'input[data-attribute_name="Never attribute size custom"][data-value_name="Yes never custom"]',
            run: "check",
        },
        {
            trigger: 'input.variant_custom_value',
            run: "edit TEST",
        },
        {
            content: "Click add to cart",
            trigger: '#add_to_cart',
            run: "click",
        },
        {
            trigger:
                ".modal:contains(configure your product) table.o_sale_product_configurator_table",
        },
        {
            content: "Go through the modal window of the product configurator",
            trigger: ".modal:contains(configure your product) button:contains(Proceed to Checkout)",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Check the product is in the cart",
            trigger: 'div>a>h6:contains(Short (TEST))',
        },
        {
            content: "Check always variant",
            trigger: 'div>a>h6:contains(M always)',
        },
        {
            content: "Check dynamic variant",
            trigger: 'div>a>h6:contains(M dynamic)',
        },
        {
            content: "Check never variant",
            trigger: 'div.text-muted>span:contains(Never attribute size: M never)',
        },
        {
            content: "Check never custom variant",
            trigger: 'div.text-muted>span:contains(Never attribute size custom: Yes never custom: TEST)',
        }
    ]});
