import { registry } from '@web/core/registry';

registry.category('web_tour.tours').add('website_sale.variant_availability', {
    steps: () => [
        {
            content: "ensure red is selected as the starting point",
            trigger: 'input[data-attribute-name="Color"][data-value-name="red"]',
            run: 'click',
        },
        {
            content: "select S; (blue, S) is sold out, so blue must be muted",
            trigger: 'input[data-attribute-name="Size"][data-value-name="S"]',
            run: 'click',
        },
        {
            content: "check blue is struck through but still clickable",
            trigger: 'input[data-value-name="blue"].o_wsale_sold_out:not([disabled])',
        },
        {
            content: "check blue also carries the shared muted styling",
            trigger: 'input[data-value-name="blue"].css_not_available',
        },
        {
            content: "pick another no_variant option; this must not affect variant marking",
            trigger: 'input[data-attribute-name="No variant"][data-value-name="second"]',
            run: 'click',
        },
        {
            content: "blue is still muted after picking an option",
            trigger: 'input[data-value-name="blue"].o_wsale_sold_out:not([disabled])',
        },
        {
            content: "the other option is never stock-marked",
            trigger: 'input[data-value-name="extra"]:not(.o_wsale_sold_out):not(.css_not_available)',
        },
        {
            content: "switch size to M; (blue, M) is in stock",
            trigger: 'input[data-attribute-name="Size"][data-value-name="M"]',
            run: 'click',
        },
        {
            content: "check blue is not muted anymore",
            trigger: 'input[data-value-name="blue"]:not(.o_wsale_sold_out)',
        },
        {
            content: "select blue; (blue, M) is a valid, in-stock combination",
            trigger: 'input[data-attribute-name="Color"][data-value-name="blue"]',
            run: 'click',
        },
        {
            content: "with blue selected, S is now the muted neighbor",
            trigger: 'input[data-value-name="S"].o_wsale_sold_out:not([disabled])',
        },
        {
            content: "the muted value is still selectable: select the sold-out combination",
            trigger: 'input[data-value-name="S"].o_wsale_sold_out',
            run: 'click',
        },
        {
            content: "once selected, S is no longer marked (selected values are never crossed)",
            trigger: 'input[data-value-name="S"]:checked:not(.o_wsale_sold_out):not(.css_not_available)',
        },
        {
            content: "blue, also selected, is not marked either",
            trigger: 'input[data-value-name="blue"]:checked:not(.o_wsale_sold_out):not(.css_not_available)',
        },
        {
            content: "the sold-out state hides the add-to-cart CTA",
            trigger: '#add_to_cart_wrap:not(:visible)',
        },
    ],
});

registry.category('web_tour.tours').add('website_sale.shop_variant_availability', {
    steps: () => [
        {
            content: "blue has no purchasable variant left: it is muted on the card",
            trigger: '.oe_product_cart[aria-label="Test Sofa"] .o_wsale_ptav_unavailable .o_wsale_product_ptav_pill_label:contains(blue)',
        },
        {
            content: "red can still be bought: it is not muted",
            trigger: '.oe_product_cart[aria-label="Test Sofa"] .o_product_variant_preview:not(.o_wsale_ptav_unavailable) .o_wsale_product_ptav_pill_label:contains(red)',
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
            content: "red can still be bought, but not in S: follow it",
            trigger: '.oe_product_cart[aria-label="Test Sofa"] a.o_product_variant_preview:not(.o_wsale_ptav_unavailable):contains(red)',
            run: 'click',
            expectUnloadPage: true,
        },
        {
            content: "the clicked value is selected",
            trigger: 'input[data-attribute-name="Color"][data-value-name="red"]:checked',
        },
        {
            content: "the size was completed with M, skipping the sold-out S",
            trigger: 'input[data-attribute-name="Size"][data-value-name="M"]:checked',
        },
        {
            content: "the landing combination can be added to the cart",
            trigger: '#add_to_cart_wrap:visible',
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
            content: "the default (red, S) is sold out, so the color moved to blue",
            trigger: 'input[data-attribute-name="Color"][data-value-name="blue"]:checked',
        },
        {
            content: "the landing combination can be added to the cart",
            trigger: '#add_to_cart_wrap:visible',
        },
    ],
});
