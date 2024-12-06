import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

function assertState(expectedState) {
    // :checked doesn't seem to work in the trigger, so let's check manually.
    const select_value = document.querySelector('select[name="state_id"]').value;
    const option = document.querySelector(
        `select[name="state_id"] option[value="${select_value}"]`
    );
    if (!option.innerText.includes(expectedState)) {
        throw new Error("The right state was not auto-selected.");
    }
}

registry.category("web_tour.tours").add("test_brazilian_address", {
    url: "/shop?search=Brazilian test product",
    checkDelay: 500,
    steps: () => [
        ...tourUtils.addToCart({ productName: "Brazilian test product", search: false }),
        tourUtils.goToCart({ quantity: 1 }),
        tourUtils.goToCheckout(),
        {
            content: "base_address_extended should not be shown",
            trigger: 'select[name="city_id"]:not(:visible)',
        },
        {
            content: "Set Brazil first",
            trigger: 'select[name="country_id"]',
            run: "selectByLabel Brazil",
        },
        {
            content: "Click to select a city",
            trigger: ".o_select_menu_toggler",
            run: "click",
        },
        {
            content: "Select Abadia de Goiás",
            trigger: ".o_select_menu_menu > span:first",
            run: "click",
        },
        {
            content: "Check that Abadia de Goiás is selected",
            trigger: '.o_select_city:contains("Abadia de Goiás")',
        },
        {
            content: "Check that Goiás state is automatically selected based on the city.",
            trigger: 'select[name="country_id"]',
            run: () => assertState("Goiás"),
        },
        {
            content: "Input a zip",
            trigger: 'input[name="zip"]',
            run: "fill 12345-000",
        },
        {
            content: "Check that Jacareí is selected",
            trigger: '.o_select_city:contains("Jacareí")',
        },
        {
            content: "Check that São Paulo state is automatically selected based on the city.",
            trigger: 'select[name="country_id"]',
            run: () => assertState("São Paulo"),
        },
    ],
});
