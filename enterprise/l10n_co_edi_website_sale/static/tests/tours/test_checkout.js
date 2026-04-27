/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("test_checkout_id_nit", {
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
            run: "selectByLabel Colombia",
        },
        {
            trigger: "input[name=name]",
            run: "edit abc",
        },
        {
            trigger: "input[name=phone]",
            run: "edit 99999999",
        },
        {
            trigger: "input[name=email]",
            run: "edit abc@odoo.com",
        },
        {
            trigger: "input[name=street]",
            run: "edit SO1 Billing Street, 33",
        },
        {
            trigger: "input[name=zip]",
            run: "edit 10000",
        },
        {
            trigger: "input[name=company_name]",
            run: "edit Test Name",
        },
        {
            trigger: "input[name=vat]",
            run: "edit 213123432-1",
        },
        {
            trigger: "select[name=state_id]",
            run: "selectByIndex 1",
        },
        {
            trigger: "select[name=city_id]",
            run: "selectByIndex 1",
        },
        {
            trigger: "select[name=l10n_latam_identification_type_id]",
            run: "selectByIndex 1",
        },
        {
            trigger: "select[name=l10n_co_edi_obligation_type_ids]:not(:visible)",
            run: "selectByLabel R-99-PN",
        },
        {
            content: "Continue Checkout",
            trigger: '.btn-primary:contains("Continue checkout")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: "h4:contains(delivery address)",
        },
    ],
});

registry.category("web_tour.tours").add("test_checkout_other_id", {
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
            run: "selectByLabel Colombia",
        },
        {
            trigger: "input[name=name]",
            run: "edit abc",
        },
        {
            trigger: "input[name=phone]",
            run: "edit 99999999",
        },
        {
            trigger: "input[name=email]",
            run: "edit abc@odoo.com",
        },
        {
            trigger: "input[name=street]",
            run: "edit SO1 Billing Street, 33",
        },
        {
            trigger: "input[name=zip]",
            run: "edit 10000",
        },
        {
            trigger: "input[name=company_name]",
            run: "edit Test Name",
        },
        {
            trigger: "input[name=vat]",
            run: "edit 213123432-1",
        },
        {
            trigger: "select[name=state_id]",
            run: "selectByIndex 1",
        },
        {
            trigger: "select[name=city_id]",
            run: "selectByIndex 1",
        },
        {
            trigger: "select[name=l10n_latam_identification_type_id]",
            run: "selectByLabel Registro Civil",
        },
        {
            content: "Validate address",
            trigger: '.btn-primary:contains("Continue checkout")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: "h4:contains(delivery address)",
        },
    ],
});
