import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("autocomplete_address_tour", {
    url: "/odoo/companies",
    steps: () => [
        {
            content: "click on new button to create a new record",
            trigger: ".o_list_button_add",
            run: "click",
        },
        {
            content: "Input in Street & Number field",
            trigger: 'div[name="street"] input',
            run: "edit This is a test",
        },
        {
            content: "Check if results have appeared",
            trigger: ".o-autocomplete--dropdown-item .dropdown-item",
        },
        {
            content: "Input again in street field",
            trigger: 'div[name="street"] input',
            run: "edit add more",
        },
        {
            content: "Click on the first result",
            trigger: ".o-autocomplete--dropdown-item .dropdown-item:contains(Result 0)",
            run: "click",
        },
        {
            content: "Check Street & number have been set",
            trigger: 'div[name="street"] input:value("42 A fictional Street")',
        },
        {
            content: "Check Street2 have been set",
            trigger: 'div[name="street2"] input:value("A fictional Street 2")',
        },
        {
            content: "Check City is not empty anymore",
            trigger: 'div[name="city"] input:value("A Fictional City")',
        },
        {
            content: "Check Zip code is not empty anymore",
            trigger: 'div[name="zip"] input:value("12345")',
        },
        {
            content: "Check Country is not empty anymore",
            trigger: 'div[name="country_id"] input:value("United States")',
        },
        {
            content: "Check State is not empty anymore",
            trigger: 'div[name="state_id"] input:value("Alabama")',
        },
        ...stepUtils.discardForm(),
    ],
});
