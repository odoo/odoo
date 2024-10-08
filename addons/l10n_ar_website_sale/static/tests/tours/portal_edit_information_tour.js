import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('portal_edit_information', {
    test: true,
    url: '/my',
    steps: () => [
        {
            content: "Check Edit Information button available",
            trigger: 'a[href*="/my/account"]:contains("Edit Information"):first',
            run: "click",
        },
        {
            content: "Submit the form",
            trigger: 'button[type=submit]',
            run: "click",
        },
        {
            content: "Check that we are back on the portal",
            trigger: 'a[href*="/my/account"]:contains("Edit Information"):first',
        }
    ]
});
