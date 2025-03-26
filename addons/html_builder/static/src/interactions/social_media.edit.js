import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class SocialMediaEdit extends Interaction {
    static selector = ".s_social_media > :first-child";

    setup() {
        this.renderAt("html_builder.empty_social_media_alert", {}, undefined, "afterend");
    }
}

registry.category("public.interactions.edit").add("html_builder.social_media_edit", {
    Interaction: SocialMediaEdit,
});
