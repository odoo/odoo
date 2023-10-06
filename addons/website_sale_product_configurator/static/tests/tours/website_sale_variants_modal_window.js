/** @odoo-module **/

    import { registry } from "@web/core/registry";

    // This tour relies on a data created from the python test.
    registry.category("web_tour.tours").add('tour_variants_modal_window', {
        test: true,
        url: '/shop?search=Short (TEST)',
        steps: () => [
        {
            content: "Select the Short (TEST) product",
            trigger: '.oe_product_cart a:containsExact("Short (TEST)")',
        },
        {
            content: "Click on the always variant",
            trigger: 'input[data-attribute_name="Always attribute size"][data-value_name="M always"]',
        },
        {
            content: "Click on the dynamic variant",
            trigger: 'input[data-attribute_name="Dynamic attribute size"][data-value_name="M dynamic"]',
        },
        {
            content: "Click on the never variant",
            trigger: 'input[data-attribute_name="Never attribute size"][data-value_name="M never"]',
        },
        {
            content: "Click on the never custom variant",
            trigger: 'input[data-attribute_name="Never attribute size custom"][data-value_name="Yes never custom"]',
        },
        {
            trigger: 'input.variant_custom_value',
            run: 'text TEST',
        },
        {
            content: "Click add to cart",
            trigger: '#add_to_cart',
        },
        {
            content: "Go through the modal window of the product configurator",
            extra_trigger: '.oe_advanced_configurator_modal',
            trigger: 'button span:contains(Proceed to Checkout)',
            run: 'click'
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
            isCheck: true,
        }
    ]});
