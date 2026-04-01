import { registry } from '@web/core/registry';

registry.category('web_tour.tours').add('website_sale_product_pricelist_qty_change', {
    steps: () => [
        {
            content: "Price should be $20",
            trigger: '.product_price:contains(20.0)',
        },
        {
            content: "Change quantity to 5",
            trigger: 'input.quantity',
            run: 'edit 5 && click body',
        },
        {
            content: "Price should now be $10",
            trigger: '.product_price:contains(10.0)',
        },
    ],
});
