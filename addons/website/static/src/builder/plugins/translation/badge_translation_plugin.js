import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class BadgeTranslationPlugin extends Plugin {
    static id = "badgeTranslation";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        force_background_translation_state_selectors: "span.s_badge",
        is_node_splittable_predicates: (node) => {
            if (node.classList?.contains("s_badge")) {
                return false;
            }
        },
    };
}

registry.category("translation-plugins").add(BadgeTranslationPlugin.id, BadgeTranslationPlugin);
