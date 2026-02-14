import { registry } from '@web/core/registry';

registry.category('web_tour.tours').add('website_sale_contact_us_button', {
    steps: () => [
        {
            content: "Check that the red color attribute is selected",
            trigger: '.js_attribute_value:has([checked]):contains(red)',
        },
        {
            content: "Product price should be 20",
            trigger: '.product_price .oe_currency_value:contains(20.00)',
        },
        {
            content: '"Add to Cart" button should be visibile',
            trigger: '#add_to_cart_wrap',
        },
        {
            content: '"Contact Us" button should be hidden',
            trigger: '#contact_us_wrapper:not(:visible)',
        },
        {
            content: "Select attribute with price zero value",
            trigger: '.js_attribute_value:contains(blue) input',
            run: 'click',
        },
        {
            content: "Zero-priced product should be unavailable",
            trigger: '#product_unavailable',
        },
        {
            content: "Price should be hidden",
            trigger: '.product_price:not(:visible)',
        },
        {
            content: '"Add to Cart" button should be hidden',
            trigger: '#add_to_cart_wrap:not(:visible)',
        },
        {
            content: '"Contact Us" button should be visible',
            trigger: '#contact_us_wrapper',
        },
    ],
});
