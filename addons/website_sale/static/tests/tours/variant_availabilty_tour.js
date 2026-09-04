import { registry } from '@web/core/registry';

registry.category('web_tour.tours').add('website_sale.variant_availability', {
    steps: () => [
        {
            content: "ensure Wood is selected as the starting point",
            trigger: 'input[data-attribute-name="Material"][data-value-name="Wood"]',
            run: 'click',
        },
        {
            content: "select White; (Steel, White) is sold out, so Steel must be muted",
            trigger: 'input[data-attribute-name="Color"][data-value-name="White"]',
            run: 'click',
        },
        {
            content: "check Steel is struck through but still clickable",
            trigger: 'input[data-value-name="Steel"].o_wsale_sold_out:not([disabled])',
        },
        {
            content: "check Steel also carries the shared muted styling",
            trigger: 'input[data-value-name="Steel"].css_not_available',
        },
        {
            content: "tick a no_variant option; this must not affect variant marking",
            trigger: 'input[data-attribute-name="Options"][data-value-name="Drawers"]',
            run: 'click',
        },
        {
            content: "Steel is still muted after ticking an option",
            trigger: 'input[data-value-name="Steel"].o_wsale_sold_out:not([disabled])',
        },
        {
            content: "the option itself is never stock-marked",
            trigger: 'input[data-value-name="Drawers"]:not(.o_wsale_sold_out):not(.css_not_available)',
        },
        {
            content: "switch color to Black; (Steel, Black) is in stock",
            trigger: 'input[data-attribute-name="Color"][data-value-name="Black"]',
            run: 'click',
        },
        {
            content: "check Steel is not muted anymore",
            trigger: 'input[data-value-name="Steel"]:not(.o_wsale_sold_out)',
        },
        {
            content: "select Steel; (Steel, Black) is a valid, in-stock combination",
            trigger: 'input[data-attribute-name="Material"][data-value-name="Steel"]',
            run: 'click',
        },
        {
            content: "with Steel selected, White is now the muted neighbor",
            trigger: 'input[data-value-name="White"].o_wsale_sold_out:not([disabled])',
        },
        {
            content: "the muted value is still selectable: select the sold-out combination",
            trigger: 'input[data-value-name="White"].o_wsale_sold_out',
            run: 'click',
        },
        {
            content: "once selected, White is no longer marked (selected values are never crossed)",
            trigger: 'input[data-value-name="White"]:checked:not(.o_wsale_sold_out):not(.css_not_available)',
        },
        {
            content: "Steel, also selected, is not marked either",
            trigger: 'input[data-value-name="Steel"]:checked:not(.o_wsale_sold_out):not(.css_not_available)',
        },
        {
            content: "the sold-out state hides the add-to-cart CTA",
            trigger: '#o_wsale_cta_wrapper.out_of_stock:not(:visible)',
        },
    ],
});

registry.category('web_tour.tours').add('website_sale.shop_variant_availability', {
    steps: () => [
        {
            content: "Steel has no purchasable variant left: it is muted on the card",
            trigger: '.oe_product_cart[aria-label="Test Sofa"] .o_wsale_ptav_unavailable .o_wsale_product_ptav_pill_label:contains(Steel)',
        },
        {
            content: "Wood can still be bought: it is not muted",
            trigger: '.oe_product_cart[aria-label="Test Sofa"] .o_product_variant_preview:not(.o_wsale_ptav_unavailable) .o_wsale_product_ptav_pill_label:contains(Wood)',
        },
        {
            content: "the muted value stays a link: follow it",
            trigger: '.oe_product_cart[aria-label="Test Sofa"] a.o_wsale_ptav_unavailable[href]',
            run: 'click',
            expectUnloadPage: true,
        },
        {
            content: "it opens the product page",
            trigger: '#product_details',
        },
    ],
});

registry.category('web_tour.tours').add('website_sale.shop_variant_availability_landing', {
    steps: () => [
        {
            content: "Wood can still be bought, but not in White: follow it",
            trigger: '.oe_product_cart[aria-label="Test Sofa"] a.o_product_variant_preview:not(.o_wsale_ptav_unavailable):contains(Wood)',
            run: 'click',
            expectUnloadPage: true,
        },
        {
            content: "the clicked value is selected",
            trigger: 'input[data-attribute-name="Material"][data-value-name="Wood"]:checked',
        },
        {
            content: "the color was completed with Black, skipping the sold-out White",
            trigger: 'input[data-attribute-name="Color"][data-value-name="Black"]:checked',
        },
        {
            content: "the landing combination can be added to the cart",
            trigger: '#o_wsale_cta_wrapper:not(.out_of_stock)',
        },
    ],
});

registry.category('web_tour.tours').add('website_sale.shop_variant_availability_tile_landing', {
    steps: () => [
        {
            content: "the card isn't marked out of stock: other variants can still be bought",
            // An empty ribbon is still rendered, only hidden, so assert on the card
            trigger: '.oe_product_cart[aria-label="Test Sofa"]:not(:has(.o_ribbons[data-ribbon-id]))',
        },
        {
            content: "open the product from the tile itself, without picking any value",
            trigger: '.oe_product_cart[aria-label="Test Sofa"] a.oe_product_image_link',
            run: 'click',
            expectUnloadPage: true,
        },
        {
            content: "the default (Wood, White) is sold out, so the color moved to Black",
            trigger: 'input[data-attribute-name="Color"][data-value-name="Black"]:checked',
        },
        {
            content: "the landing combination can be added to the cart",
            trigger: '#o_wsale_cta_wrapper:not(.out_of_stock)',
        },
    ],
});
