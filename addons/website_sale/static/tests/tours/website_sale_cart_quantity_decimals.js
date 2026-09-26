import { registry } from '@web/core/registry';
import configuratorTourUtils from '@sale/js/tours/product_configurator_tour_utils';
import * as tourUtils from '@website_sale/js/tours/tour_utils';

function cartLineQuantity(productName) {
    return `.o_cart_product:has(h6:contains("${productName}")) input.js_quantity`;
}

function configuratorQuantity(productName) {
    return `${configuratorTourUtils.productSelector(productName).trim()}
        td.o_sale_product_configurator_qty input[name="sale_quantity"]`;
}

registry.category('web_tour.tours').add('website_sale_cart_quantity_decimals', {
    url: '/shop',
    steps: () => [
        // Product page: continuous UoMs keep their decimals.
        ...tourUtils.searchProduct("Decimal Powder", { select: true }),
        {
            content: "Set 2.5 kg of powder",
            trigger: 'input[name="add_qty"]',
            run: "edit 2.5 && click body",
        },
        { trigger: '#add_to_cart', run: "click" },
        { trigger: 'a sup.my_cart_quantity:text(1)' },
        { trigger: "a[href='/shop']", run: "click", expectUnloadPage: true },
        // Product page: other UoMs only allow integer quantities.
        ...tourUtils.searchProduct("Decimal Bolt", { select: true }),
        {
            content: "Set 2.5 bolts",
            trigger: 'input[name="add_qty"]',
            run: "edit 2.5 && click body",
        },
        {
            content: "The bolt quantity is truncated to an integer",
            trigger: 'input[name="add_qty"]:value(/^2$/)',
        },
        { trigger: '#add_to_cart', run: "click" },
        // Product configurator: other UoMs only allow integer quantities.
        { trigger: `${configuratorQuantity("Decimal Bolt")}:value(/^2$/)` },
        {
            content: "Set 3.7 bolts",
            trigger: configuratorQuantity("Decimal Bolt"),
            // Typed character by character, the intermediate "3." is not a valid value for a
            // number input and would be dropped, so the value is set at once.
            run() {
                this.anchor.value = "3.7";
                this.anchor.dispatchEvent(new Event("input", { bubbles: true }));
                this.anchor.dispatchEvent(new Event("change", { bubbles: true }));
            },
        },
        {
            content: "The bolt quantity is truncated to an integer",
            trigger: `${configuratorQuantity("Decimal Bolt")}:value(/^3$/)`,
        },
        {
            trigger: 'button[name="website_sale_product_configurator_continue_button"]',
            run: "click",
        },
        // Cart: the powder line counts as one item, the bolts are summed.
        tourUtils.goToCart({ quantity: 4 }),
        // The `value` attribute is only set when the cart lines are rendered by the server,
        // unlike the typed value.
        { trigger: `${cartLineQuantity("Decimal Powder")}[value="2.5"]` },
        { trigger: `${cartLineQuantity("Decimal Bolt")}[value="3"]` },
        {
            content: "Set 3.5 kg of powder",
            trigger: cartLineQuantity("Decimal Powder"),
            run: "edit 3.5 && click body",
        },
        {
            content: "The powder quantity keeps its decimals",
            trigger: `${cartLineQuantity("Decimal Powder")}[value="3.5"]`,
        },
        {
            content: "Set 4.7 bolts",
            trigger: cartLineQuantity("Decimal Bolt"),
            run: "edit 4.7 && click body",
        },
        {
            content: "The bolt quantity is truncated to an integer",
            trigger: `${cartLineQuantity("Decimal Bolt")}[value="4"]`,
        },
        { trigger: 'a sup.my_cart_quantity:text(5)' },
    ],
});
