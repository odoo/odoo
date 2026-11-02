
import { registry } from "@web/core/registry";

// No website_sale import: this module does not depend on it.
registry.category("web_tour.tours").add('autocomplete_tour', {
    steps: () => [
        {
            content: "Add the product to the cart",
            trigger: '.js_product button[name="add_to_cart"]',
            run: "click",
        }, {
            content: "Go to cart",
            trigger: "a sup.my_cart_quantity:text(1)",
            run: "click",
            expectUnloadPage: true,
        }, {
            content: "Checkout your order",
            trigger: 'a[href^="/shop/checkout"]',
            run: "click",
            expectUnloadPage: true,
        }, { // Actual test
            content: 'Input in Street & Number field',
            trigger: 'input[name="street"]',
            run: "edit This is a test",
        }, {
            content: 'Check if results have appeared',
            trigger: '.js_autocomplete_result',
        }, {
            content: 'Input again in street field',
            trigger: 'input[name="street"]',
            run: "fill add more",
        }, {
            content: 'Click on the first result',
            trigger: ".dropdown-menu .js_autocomplete_result:first:contains(result 0)",
            run: "click",
        },
        // TODO: Make this step work in headless mode
        // {
        //     content: "Verify the autocomplete box disappeared",
        //     trigger: `body:not(:has(.dropdown-menu .js_autocomplete_result))`,
        // },
        { // Verify test data has been input
            content: 'Check Street & number have been set',
            trigger: "input[name=street]:value(/^42 A fictional Street$/)",
        }, {
            content: 'Check City is not empty anymore',
            trigger: 'input[name="city"]:value(/^A Fictional City$/)',
        }, {
            content: 'Check Zip code is not empty anymore',
            trigger: 'input[name="zip"]:value(/^12345$/)',
        }]
});
