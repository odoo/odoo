import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class LoveOptionPlugin extends Plugin {
    static id = "loveOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        mark_color_level_selector_params: [{ selector: ".s_love_review" }],
    };
}

registry.category("website-plugins").add(LoveOptionPlugin.id, LoveOptionPlugin);
