import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class BlogPageOptionPlugin extends Plugin {
    static id = "blogPageOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        content_not_editable_selectors: [".o_list_cover"],
    };
}

registry.category("website-plugins").add(BlogPageOptionPlugin.id, BlogPageOptionPlugin);
