import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("portal_compute_codice_fiscale", {
    steps: () => [
        {
            content: "Check portal is loaded",
            trigger: 'a[href*="/my/account"]:contains("Edit"):first',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Load my account details",
            trigger: 'input[value="IT User"]',
            run: "click",
        },
        {
            content: "Fill address form: phone",
            trigger: `form.address_autoformat input[name="phone"]`,
            run: "edit 99999999",
        },
        {
            content: "Fill address form: email",
            trigger: `form.address_autoformat input[name="email"]`,
            run: "edit abc@odoo.com",
        },
        {
            content: "Fill address form: vat",
            trigger: `form.address_autoformat input[name="vat"]`,
            run: "edit IT12345670017",
        },
        {
            content: "Fill address form: street",
            trigger: `form.address_autoformat input[name="street"]`,
            run: "edit SO1 Billing Street, 33",
        },
        {
            content: "Fill address form: city",
            trigger: `form.address_autoformat input[name="city"]`,
            run: "edit SO1BillingCity",
        },
        {
            content: "Fill address form: zip",
            trigger: `form.address_autoformat input[name="zip"]`,
            run: "edit 10000",
        },
        {
            id: "o_country_id",
            content: "Select country with code 'IT' to trigger compute of Codice Fiscale",
            trigger: 'select[name="country_id"]',
            run: `selectByLabel Italy`,
        },
        {
            content: "Check if the Codice Fiscale value matches",
            trigger: "input[name='l10n_it_codice_fiscale']:value(12345670017)",
        },
        {
            content: "Add state",
            trigger: 'select[name="state_id"]',
            run: "selectByIndex 2",
        },
        {
            content: "Submit the form",
            trigger: "button[id=save_address]",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Check that we are back on the portal",
            trigger: 'a[href*="/my/account"]:contains("Edit"):first',
        },
    ],
});
