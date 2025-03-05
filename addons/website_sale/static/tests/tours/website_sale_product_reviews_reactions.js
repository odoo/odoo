import { registry } from "@web/core/registry";

registry
    .category('web_tour.tours')
    .add('website_sale_product_reviews_reactions', {
        url: '/shop?search=Storage Box Test',
        steps: () => [
            {
                trigger: '.oe_product_cart a:contains("Storage Box Test")',
                run: "click",
            },
        ],
   });
