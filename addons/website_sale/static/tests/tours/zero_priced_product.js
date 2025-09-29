import { registry } from '@web/core/registry';

registry.category('web_tour.tours').add('website_sale_contact_us_button', {
    steps: () => [
        {
            content: "Check that the red color attribute is selected",
            trigger: '.js_attribute_value:has([checked]):contains(red)',
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
        {
            content: "Select attribute with price extra value",
            trigger: '.js_attribute_value:contains(blue):contains(20.00) input',
            run: 'click',
        },
        {
            content: "Product price should be updated",
            trigger: '.product_price .oe_currency_value:contains(20.00)',
        },
        {
            content: '"Add to Cart" button should now be visibile',
            trigger: '#add_to_cart_wrap',
        },
        {
            content: '"Contact Us" button should now be hidden',
            trigger: '#contact_us_wrapper:not(:visible)',
        },
    ],
});
