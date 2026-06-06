import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class SeparatorOptionPlugin extends Plugin {
    static id = "separatorOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        dropzone_selectors: {
            selector: ".s_hr",
            dropNear: "p, h1, h2, h3, blockquote, .s_hr",
            excludeAncestor:
                ".s_map, .s_google_map, .s_website_form_label, .s_announcement_scroll_marquee_container",
        },
        so_content_addition_selectors: [".s_hr"],
        is_movable_selectors: { selector: ".s_hr", direction: "vertical" },
    };
}

registry.category("builder-plugins").add(SeparatorOptionPlugin.id, SeparatorOptionPlugin);
