import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("portal_chatter_bundle", {
    steps: () => [
        {
            trigger: 'a:contains("Gardening: The Know-How")',
            content: "Check that the previews are accessible",
        },
        {
            trigger: "a[id=review-tab]",
            run: "click",
        },
        {
            content: "Wait for the whole page to load",
            trigger: "#chatterRoot:shadow .o-mail-Chatter",
            run: () => odoo.portalChatterReady,
        },
    ],
});
