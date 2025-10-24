import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class BlogPostListPageOption extends BaseOptionComponent {
    static template = "website_blog.blogPostListPageOption";
    static selector = "main:has(#o_wblog_index_content)";
    static title = _t("Blogs Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

export class BlogPostListPageOptionPlugin extends Plugin {
    static id = "blogPostPageListOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [BlogPostListPageOption],
    };
}

registry
    .category("website-plugins")
    .add(BlogPostListPageOptionPlugin.id, BlogPostListPageOptionPlugin);
