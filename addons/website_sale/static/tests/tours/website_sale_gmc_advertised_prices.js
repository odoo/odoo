import { registry } from '@web/core/registry';

registry.category('web_tour.tours').add('website_sale_gmc_check_advertised_prices_white_mouse_usd', {
    steps: () => [
        {
            content: 'Check price',
            trigger: 'span.oe_price:contains("79.00")'
        },
        {
            content: 'Check currency',
            trigger: 'span[itemprop="priceCurrency"]:contains("USD"):not(:visible)'
        },
]});

registry.category('web_tour.tours').add('website_sale_gmc_check_advertised_prices_black_mouse_usd', {
    steps: () => [
        {
            content: 'Check price',
            trigger: 'span.oe_price:contains("99.00")',
        },
        {
            content: 'Check currency',
            trigger: 'span[itemprop="priceCurrency"]:contains("USD"):not(:visible)'
        },
]});

registry.category('web_tour.tours').add('website_sale_gmc_check_advertised_prices_white_mouse_christmas', {
    steps: () => [
        {
            content: 'Check price',
            trigger: 'span.oe_price:contains("78.21")', // 79.0 * 1.1 (EUR rate) - 10% discount
        },
        {
            content: 'Check currency',
            trigger: 'span[itemprop="priceCurrency"]:contains("EUR"):not(:visible)'
        },
]});

registry.category('web_tour.tours').add('website_sale_gmc_check_advertised_prices_black_mouse_christmas', {
    steps: () => [
        {
            content: 'Check price',
            trigger: 'span.oe_price:contains("98.01")', // 99.0 * 1.1 (EUR rate) - 10% discount
        },
        {
            content: 'Check currency',
            trigger: 'span[itemprop="priceCurrency"]:contains("EUR"):not(:visible)'
        },
]});

registry.category('web_tour.tours').add('website_sale_gmc_check_advertised_prices_white_mouse_tax_included', {
    steps: () => [
        {
            content: 'Check price',
            trigger: 'span.oe_price:contains("90.85")', // 15% tax
        },
        {
            content: 'Check currency',
            trigger: 'span[itemprop="priceCurrency"]:contains("USD"):not(:visible)'
        },
]});

registry.category('web_tour.tours').add('website_sale_gmc_check_advertised_prices_black_mouse_tax_included', {
    steps: () => [
        {
            content: 'Check price',
            trigger: 'span.oe_price:contains("113.85")', // 15% tax
        },
        {
            content: 'Check currency',
            trigger: 'span[itemprop="priceCurrency"]:contains("USD"):not(:visible)'
        },
]});