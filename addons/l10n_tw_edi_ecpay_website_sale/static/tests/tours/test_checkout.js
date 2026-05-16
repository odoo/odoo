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
            trigger: "a[name='website_sale_main_button']",
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
            run: "edit 123456789",
        },
        {
            content: "Continue Checkout",
            trigger: "a[name='website_sale_main_button']",
            run: "click",
        },
        {
            content: "Should show tax id invalid error message",
            trigger: "div:contains('Please enter a valid Tax ID')",
        },
    ],
});

registry.category("web_tour.tours").add("test_checkout_b2c_carrier", {
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
            trigger: "a[name='website_sale_main_button']",
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

registry.category("web_tour.tours").add("test_checkout_b2c_love_code", {
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
            trigger: "a[name='website_sale_main_button']",
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
            trigger: "input[name=l10n_tw_edi_is_donate]",
            run: "click",
        },
        {
            trigger: "input[name=l10n_tw_edi_love_code]",
            run: "edit 123",
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
            run: "edit BE0477472701",
        },
        {
            content: "Continue Checkout",
            trigger: "a[name='website_sale_main_button']",
            run: "click",
            expectUnloadPage: true,
        },
    ],
});

registry.category("web_tour.tours").add("test_checkout_b2c_mobile_barcode", {
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
            trigger: "a[name='website_sale_main_button']",
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
            run: "selectByLabel Mobile Barcode",
        },
        {
            trigger: "input[name=l10n_tw_edi_carrier_number]",
            run: "edit /1234567",
        },
        // Valid mobile barcode, after the fix the l10n_tw_edi_carrier_type should remain "3"
        {
            content: "Validate Mobile Barcode",
            trigger: "#validate_carrier_number",
            run: "click",
            expectUnloadPage: false,
        },
        {
            content: "Continue checkout",
            trigger: "a[name='website_sale_main_button']",
            run: "click",
            expectUnloadPage: true,
        },
    ],
});
