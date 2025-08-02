/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('update_the_address_for_peru_company', {
    test: true,
    url: '/shop',
    steps: () => [
        ...tourUtils.addToCart({ productName: "Test Product" }),
        tourUtils.goToCart({ quantity: 1 }),
        {
            content: "Go to checkout",
            trigger: "a:contains('Checkout')",
            run: "click",
        },
        {
            content: "Fill vat",
            trigger: 'input[name="vat"]',
            run: "text 111111111111",
        },
        {
            content: "Fill city",
            trigger: 'input[name="city"]',
            run: "text Scranton",
        },
        {
            content: "Save address",
            trigger: 'a:contains("Save address")',
            run: "click",
        },
        {
            content: "Add new billing address",
            trigger: '.all_billing a[href^="/shop/address?mode=billing"]:contains("Add address")',
            run: "click",
        },
        ...tourUtils.fillAdressForm(),
        ...tourUtils.payWithTransfer(),
    ],
});

registry.category("web_tour.tours").add('maintain_city_district_on_reload', {
    test: true,
    url: '/shop',
    steps: () => [
        ...tourUtils.addToCart({ productName: "Test Product" }),
        tourUtils.goToCart({ quantity: 1 }),
        {
            content: "Go to checkout",
            trigger: "a:contains('Checkout')",
            run: "click",
        },
        {
            content: "Enter an initial value for the State",
            trigger: 'select[name="state_id"]',
            run: "text Lima",
        },
        {
            trigger: 'select[name="city_id"]',
            run() {},
        },
        {
            content: "Enter an initial value for the city",
            trigger: 'select[name="city_id"]',
            run: "text Lima",
        },
        {
            trigger: 'select[name="l10n_pe_district"]',
            run() {},
        },
        {
            content: "Select an initial value for the district",
            trigger: 'select[name="l10n_pe_district"]',
            run: "text Lima",
        },
        {
            content: "Enter an invalid VAT value to trigger a potential reload",
            trigger: 'input[name="vat"]',
            run: 'text XAXX010101000',
        },
        {
            content: "Save address",
            trigger: 'a:contains("Save address")',
            run: "click",
        },
        {
            content: "Wait for the page to reload",
            trigger: '.text-danger',
        },
        {
            content: "Check if the city field still has the previously entered value",
            trigger: 'select[name="city_id"]' ,
            run: () => {
                const selectElement = document.querySelector('select[name="city_id"]');
                const selectedOption = selectElement.options[selectElement.selectedIndex]
	            if (selectedOption.dataset.code != "1501") {
                    throw new Error("City has a different value");
                }
            },
        },
        {
            content: "Check if the district field still has the previously selected value",
            trigger: 'select[name="l10n_pe_district"]',
            run: () => {
                const selectElement = document.querySelector('select[name="l10n_pe_district"]');
                const selectedOption = selectElement.options[selectElement.selectedIndex]
	            if (selectedOption.dataset.code != "150101") {
                    throw new Error("District has a different value");
                }
            },
        }
    ],
});
