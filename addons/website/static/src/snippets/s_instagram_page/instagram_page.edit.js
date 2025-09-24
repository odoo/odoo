import { registry } from "@web/core/registry";
import { InstagramPage } from "./instagram_page";

const InstagramPageEdit = (I) =>
    class extends I {
        setup() {
            super.setup();
            this.dynamicContent["iframe"] = {
                "t-att-style": () => ({ "pointer-events": "none" }),
            };
        }

        getConfigurationSnapshot() {
            return this.el.dataset.instagramPage;
        }
    };

registry.category("public.interactions.edit").add("website.instagram_page", {
    Interaction: InstagramPage,
    mixin: InstagramPageEdit,
});
