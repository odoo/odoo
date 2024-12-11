import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('website_sale_gmc_check_advertised_prices_white_mouse_usd', {
    steps: () => [
        {
            content: "Check price",
            trigger: "span.oe_price:contains('79.00')"
        }, 
        {
            content: "Check currency",
            trigger: "span[itemprop='priceCurrency']:contains('USD'):not(:visible)"
        },
]});

registry.category("web_tour.tours").add('website_sale_gmc_check_advertised_prices_black_mouse_usd', {
    steps: () => [
        {
            content: "Check price",
            trigger: "span.oe_price:contains('99.00')",
        },
        {
            content: "Check currency",
            trigger: "span[itemprop='priceCurrency']:contains('USD'):not(:visible)"
        },
]});

registry.category("web_tour.tours").add('website_sale_gmc_check_advertised_prices_white_mouse_christmas', {
    steps: () => [
        {
            content: "Check price",
            trigger: "span.oe_price:contains('71.10')", // 10% discount
        },
        {
            content: "Check currency",
            trigger: "span[itemprop='priceCurrency']:contains('EUR'):not(:visible)"
        },
]});

registry.category("web_tour.tours").add('website_sale_gmc_check_advertised_prices_black_mouse_christmas', {
    steps: () => [
        {
            content: "Check price",
            trigger: "span.oe_price:contains('89.10')", // 10% discount
        },
        {
            content: "Check currency",
            trigger: "span[itemprop='priceCurrency']:contains('EUR'):not(:visible)"
        },
]});