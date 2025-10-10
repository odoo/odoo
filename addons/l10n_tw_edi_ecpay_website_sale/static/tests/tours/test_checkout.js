/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("test_validate_customer_info_error", {
    url: "/shop",
    steps: () => [
        ...tourUtils.addToCart({ productName: "Test Product", expectUnloadPage: true }),
        tourUtils.goToCart({ quantity: 1 }),
        {
            content: "Go to checkout",
            trigger: "a[name='website_sale_main_button']",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: "select[name=country_id]",
            run: "selectByLabel Taiwan",
        },
        {
            trigger: "input[name=name]",
            run: "edit Test Customer 1",
        },
        {
            trigger: "input[name=email]",
            run: "edit test@odoo.com",
        },
        {
            trigger: "input[name=street]",
            run: "edit Xinyi Road 33",
        },
        {
            trigger: "input[name=zip]",
            run: "edit 10000",
        },
        {
            trigger: "input[name=city]",
            run: "edit Taipei",
        },
        {
            trigger: "select[name=l10n_tw_edi_require_paper_format]",
            run: "selectByLabel No",
        },
        // Invalid phone number
        {
            trigger: "input[name=phone]",
            run: "edit 123+456+789",
        },
        {
            content: "Continue Checkout",
            trigger: '.btn-primary:contains("Continue checkout")',
            run: "click",
        },
        {
            content: "Should show phone number invalid error message",
            trigger: "div:contains('Phone number contains invalid characters!')",
        },
        {
            trigger: "input[name=phone]",
            run: "edit +886 123 456 789",
        },
        {
            trigger: "input[name=company_name]",
            run: "edit Test Company",
        },
        // Invalid VAT
        {
            trigger: "input[name=vat]",
            run: "edit 1234567A",
        },
        {
            content: "Continue Checkout",
            trigger: '.btn-primary:contains("Continue checkout")',
            run: "click",
        },
        {
            content: "Should show phone number invalid error message",
            trigger: "div:contains('Please enter a valid Tax ID')",
        },
    ],
});

registry.category("web_tour.tours").add("test_checkout_b2c", {
    url: "/shop",
    steps: () => [
        ...tourUtils.addToCart({ productName: "Test Product", expectUnloadPage: true }),
        tourUtils.goToCart({ quantity: 1 }),
        {
            content: "Go to checkout",
            trigger: "a[name='website_sale_main_button']",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: "select[name=country_id]",
            run: "selectByLabel Taiwan",
        },
        {
            trigger: "input[name=name]",
            run: "edit Test Customer B2C",
        },
        {
            trigger: "input[name=phone]",
            run: "edit +886 123 456 789",
        },
        {
            trigger: "input[name=email]",
            run: "edit test@odoo.com",
        },
        {
            trigger: "input[name=street]",
            run: "edit Xinyi Road 33",
        },
        {
            trigger: "input[name=zip]",
            run: "edit 10000",
        },
        {
            trigger: "input[name=city]",
            run: "edit Taipei",
        },
        {
            trigger: "select[name=l10n_tw_edi_require_paper_format]",
            run: "selectByLabel No",
        },
        {
            content: "Continue Checkout",
            trigger: '.btn-primary:contains("Continue checkout")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Confirm",
            trigger: "a[name='website_sale_main_button']",
            run: "click",
            expectUnloadPage: true,
        },
        // E-invoice info
        {
            trigger: "select[name=l10n_tw_edi_carrier_type]",
            run: "selectByLabel EasyCard",
        },
        {
            trigger: "input[name=l10n_tw_edi_carrier_number]",
            run: "edit 123",
        },
        {
            trigger: "input[name=l10n_tw_edi_carrier_number_2]",
            run: "edit 456",
        },
        {
            content: "Continue checkout",
            trigger: "a[name='website_sale_main_button']",
            run: "click",
            expectUnloadPage: true,
        },
    ],
});

registry.category("web_tour.tours").add("test_checkout_b2b", {
    url: "/shop",
    steps: () => [
        ...tourUtils.addToCart({ productName: "Test Product", expectUnloadPage: true }),
        tourUtils.goToCart({ quantity: 1 }),
        {
            content: "Go to checkout",
            trigger: "a[name='website_sale_main_button']",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: "select[name=country_id]",
            run: "selectByLabel Taiwan",
        },
        {
            trigger: "input[name=name]",
            run: "edit Test Customer B2B",
        },
        {
            trigger: "input[name=phone]",
            run: "edit +886 123 456 789",
        },
        {
            trigger: "input[name=email]",
            run: "edit test@odoo.com",
        },
        {
            trigger: "input[name=street]",
            run: "edit Xinyi Road 33",
        },
        {
            trigger: "input[name=zip]",
            run: "edit 10000",
        },
        {
            trigger: "input[name=city]",
            run: "edit Taipei",
        },
        {
            trigger: "input[name=company_name]",
            run: "edit Test Company",
        },
        {
            trigger: "input[name=vat]",
            run: "edit 12345678",
        },
        {
            content: "Continue Checkout",
            trigger: '.btn-primary:contains("Continue checkout")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Confirm",
            trigger: "a[name='website_sale_main_button']",
            run: "click",
            expectUnloadPage: true,
        },
    ],
});
