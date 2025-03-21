import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class SocialMediaOptionPlugin extends Plugin {
    static id = "socialMediaOptionPlugin";
    resources = {
        builder_options: [
            {
                template: "html_builder.SocialMediaOption",
                selector: ".s_share, .s_social_media",
            },
        ],
    };
}
registry.category("website-plugins").add(SocialMediaOptionPlugin.id, SocialMediaOptionPlugin);
