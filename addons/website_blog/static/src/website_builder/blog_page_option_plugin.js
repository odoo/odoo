import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class BlogPageOption extends BaseOptionComponent {
    static template = "website_blog.BlogPageOption";
    static selector = "main:has(#o_wblog_post_main)";
    static title = _t("Blog Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

export class BlogPageOptionPlugin extends Plugin {
    static id = "blogPageOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [BlogPageOption],
    };
}

registry.category("website-plugins").add(BlogPageOptionPlugin.id, BlogPageOptionPlugin);
