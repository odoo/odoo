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
            run: () => {
                odoo.portalChatterReady.then(() => {
                    const { missing, failed, unloaded } = odoo.loader.findErrors();
                    if ([missing, failed, unloaded].some((arr) => arr.length)) {
                        console.error(
                            "Couldn't load all JS modules.",
                            JSON.stringify({ missing, failed, unloaded })
                        );
                    } else {
                        console.log("test successful");
                    }
                });
            },
        },
    ],
});
