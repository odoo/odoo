import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

// This tour relies on a data created from the python test.
registry.category("web_tour.tours").add('website_sale.optional_products_modal', {
    steps: () => [
        {
            content: "Click on the always variant",
            trigger: 'input[data-attribute-name="Always attribute size"][data-value-name="M always"]',
            run: "check",
        },
        {
            content: "Click on the dynamic variant",
            trigger: 'input[data-attribute-name="Dynamic attribute size"][data-value-name="M dynamic"]',
            run: "check",
        },
        {
            content: "Click on the never variant",
            trigger: 'input[data-attribute-name="Never attribute size"][data-value-name="M never"]',
            run: "check",
        },
        {
            content: "Click on the never custom variant",
            trigger: 'input[data-attribute-name="Never attribute size custom"][data-value-name="Yes never custom"]',
            run: "check",
        },
        {
            trigger: 'input.variant_custom_value',
            run: "edit TEST",
        },
        ...tourUtils.addToCartFromProductPage(),
        {
            trigger:
                '.modal:has(table.o_sale_product_configurator_table)',
        },
        {
            content: "Go through the modal window of the product configurator",
            trigger: 'button:contains("Checkout")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Check the product is in the cart",
            trigger: 'div>a>h6:contains(Short (TEST))',
        },
        {
            content: "Check always variant",
            trigger: 'span[class*=h6]:contains(M always)',
        },
        {
            content: "Check dynamic variant",
            trigger: 'span[class*=h6]:contains(M dynamic)',
        },
        {
            content: "Check never variant",
            trigger: 'div.text-muted>span:contains(Never attribute size: M never)',
        },
        {
            content: "Check never custom variant",
            trigger: 'div.text-muted>span:contains(Never attribute size custom: Yes never custom: TEST)',
        }
    ]
});
