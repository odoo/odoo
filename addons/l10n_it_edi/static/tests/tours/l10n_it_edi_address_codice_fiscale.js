import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("portal_compute_codice_fiscale", {
    url: "/my",
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
            content: "Fill address form with VAT",
            trigger: "form.address_autoformat",
            run: function () {
                $('input[name="phone"]').val("99999999");
                $('input[name="email"]').val("abc@odoo.com");
                $('input[name="vat"]').val("IT12345670017");
                $('input[name="street"]').val("SO1 Billing Street, 33");
                $('input[name="city"]').val("SO1BillingCity");
                $('input[name="zip"]').val("10000");
            },
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
