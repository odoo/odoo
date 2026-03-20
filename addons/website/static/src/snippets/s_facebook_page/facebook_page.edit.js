import { FacebookPage } from "./facebook_page";
import { registry } from "@web/core/registry";

const FacebookPageEdit = (I) =>
    class extends I {
        dynamicContent = {
            iframe: {
                "t-att-style": () => ({ "pointer-events": "none" }),
            },
        };
    };

registry.category("public.interactions.edit").add("website.facebook_page", {
    Interaction: FacebookPage,
    mixin: FacebookPageEdit,
});
